import os
import time
import json
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import uvicorn
import threading
import socket
import hashlib

from consensus.block import Block
from consensus.pow import ProofOfWork
from consensus.genesis import GenesisBlock
from network.mqtt_client import MQTTClient
from energy.monitor import EnergyMonitor
from monitoring.metrics import BlockchainMetrics
from monitoring.dashboard import app as dashboard_app, set_metrics_instance
from storage.sqlite_storage import SQLiteStorage
from config.network_config import (
    get_node_config,
    RASPBERRY_PI_SETTINGS,
    NETWORK_SETTINGS,
    RASPBERRY_PI_NODES,
    MQTT_BROKERS,
    MQTT_TOPICS
)

class BlockchainNode:
    def __init__(self):
        load_dotenv()
        
        # Get node configuration
        self.node_id = os.getenv('NODE_ID', 'pi_node_1')
        self.node_config = get_node_config(self.node_id)
        
        if not self.node_config:
            raise ValueError(f"Invalid node ID: {self.node_id}")
        
        # Initialize components
        self.energy_monitor = EnergyMonitor()
        # Use node-specific database file to avoid conflicts
        db_filename = f'blockchain_{self.node_id}.db'
        self.storage = SQLiteStorage(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', db_filename))
        self.metrics = BlockchainMetrics(self.node_id, self.storage)
        set_metrics_instance(self.metrics)
        self.pow = ProofOfWork(target_block_time=3.0, metrics=self.metrics)
        print(f"[DEBUG] Initializing MQTT client for node: {self.node_id}")
        print(f"[DEBUG] Node config: {self.node_config}")
        print(f"[DEBUG] About to create MQTTClient instance...")
        self.mqtt_client = MQTTClient(self.node_id, self.node_config)
        print(f"[DEBUG] MQTTClient instance created successfully")
        
        # Initialize blockchain with genesis block
        self.blocks = []
        self._initialize_blockchain()
        
        # Setup message handlers
        self._setup_handlers()
        
        # Initialize transaction pool
        self.pending_transactions = []
        
        # Start dashboard in a separate thread
        self.dashboard_thread = threading.Thread(
            target=self._start_dashboard,
            daemon=True
        )
        
        # Initialize HTTP client for chain synchronization
        self.http_client = httpx.AsyncClient(timeout=NETWORK_SETTINGS['timeout'])
        
    def _initialize_blockchain(self) -> None:
        """Initialize blockchain with genesis block and PoW configuration."""
        # Load blocks from storage
        stored_blocks = self.storage.get_blocks()
        
        if stored_blocks:
            self.blocks = stored_blocks
            print(f"Loaded {len(self.blocks)} blocks from database.")
        else:
            # If no blocks in storage, create and save genesis block
            genesis = GenesisBlock()
            genesis_block = genesis.create_genesis_block()
            
            # Verify genesis block (optional, but good practice)
            if not genesis.verify_genesis_block(genesis_block):
                raise ValueError("Invalid genesis block after creation")
                
            self.blocks.append(genesis_block)
            self.storage.save_block(genesis_block)
            print("Created and saved genesis block.")
        
        # Verify existing genesis block (loaded or newly created)
        genesis_verifier = GenesisBlock()
        if not genesis_verifier.verify_genesis_block(self.blocks[0]):
            raise ValueError("Invalid genesis block found in chain.")

        # Initialize PoW network with initial hash rate estimate
        print(f"Blockchain initialized with genesis block for PoW consensus.")
        print(f"[INIT] PoW consensus initialized with target block time: {self.pow.target_block_time}s")

        # Initialize all_nodes_metrics with network participants and current timestamp
        current_init_time = time.time()
        # Get all nodes from configuration for metrics tracking
        all_node_ids = [node['id'] for node in RASPBERRY_PI_NODES]
        for node_id in all_node_ids:
            self.metrics.all_nodes_metrics[node_id].update({
                'node_id': node_id,
                'timestamp': current_init_time,
                'cpu_percent': 0,
                'memory_percent': 0,
                'temperature': 0,
                'power_usage': 0,
                'block_count': 0,
                'pending_transactions': 0,
                'hash_rate': 0,  # Will be updated from mining
                'is_mining': False,  # Mining status
            })
        print(f"[INIT] Initialized all_nodes_metrics with current time for miners' initial liveness: {current_init_time}")

    def _start_dashboard(self):
        """Start the dashboard server."""
        uvicorn.run(
            dashboard_app,
            host="0.0.0.0",
            port=self.node_config['dashboard_port'],
            log_level="info"
        )
        
    def _setup_handlers(self) -> None:
        """Setup MQTT message handlers."""
        self.mqtt_client.subscribe(MQTT_TOPICS["BLOCKS"], self._handle_new_block)
        self.mqtt_client.subscribe(MQTT_TOPICS["TRANSACTIONS"], self._handle_new_transaction)
        self.mqtt_client.subscribe(MQTT_TOPICS["NETWORK_STATUS"], self._handle_network_status)
        self.mqtt_client.subscribe(MQTT_TOPICS["MINER_STATUS"], self._handle_miner_status)
        self.mqtt_client.subscribe(MQTT_TOPICS["METRICS"], self._handle_incoming_metrics)
        
    def _handle_new_block(self, block_data: dict) -> None:
        """Handle incoming new block with Bitcoin-style consensus rules."""
        block = Block.from_dict(block_data)
        print(f"[HANDLE BLOCK] Node {self.node_id} received new block: {block.hash} (Block Index: {block.block_index})")
        
        # Skip if we already have this block
        if any(b.hash == block.hash for b in self.blocks):
            print(f"[HANDLE BLOCK] Block {block.hash} already exists in chain.")
            return
        
        # Check if this is an orphan block (parent not found)
        if self.blocks and block.previous_hash != self.blocks[-1].hash:
            if self.pow.handle_orphan_block(block):
                print(f"[HANDLE BLOCK] Stored orphan block {block.hash} for later processing")
                return
        
        # Determine previous block's details for validation
        previous_block_timestamp = self.blocks[-1].timestamp if self.blocks else 0.0
        previous_block_index = self.blocks[-1].block_index if self.blocks else -1

        if not self.blocks and block.block_index == 0:  # Genesis block
            previous_block_timestamp = 0.0
            previous_block_index = -1

        # Check energy metrics before validation
        energy_metrics = self.energy_monitor.get_system_metrics()
        if self.pow.validate_block(block, energy_metrics['power_usage'], previous_block_timestamp, previous_block_index):
            print(f"[HANDLE BLOCK] Block {block.hash} validation successful.")
            
            # Add block to local chain
            self.blocks.append(block)
            self.storage.save_block(block)
            
            # Process any pending orphan blocks
            self.blocks = self.pow.process_pending_blocks(self.blocks)
            
            # Resolve forks and get the best chain
            all_blocks = self.storage.get_blocks()  # Get all blocks from storage
            best_chain = self.pow.resolve_forks(all_blocks)
            
            # Check if we need to switch to a better chain
            if len(best_chain) > len(self.blocks) or self.pow.calculate_chain_work(best_chain) > self.pow.calculate_chain_work(self.blocks):
                print(f"[HANDLE BLOCK] Switching to better chain: {len(best_chain)} blocks with {self.pow.calculate_chain_work(best_chain)} work")
                self.blocks = best_chain
                # Update storage with the best chain
                for block in best_chain:
                    self.storage.save_block(block)
            
            # Record metrics
            if len(self.blocks) > 1:
                self.metrics.record_block_time(block.timestamp - previous_block_timestamp)
                self.metrics.record_consensus_time(
                    block.energy_metrics.get('consensus_time', 0)
                )
            
            # Persist per-block analytics
            try:
                interval = block.timestamp - previous_block_timestamp
                consensus_time = block.energy_metrics.get('consensus_time', 0)
                power_usage = block.energy_metrics.get('power_usage', 0)
                self.storage.save_block_metrics(block.block_index, block.timestamp, interval, consensus_time, power_usage)
            except Exception as e:
                print(f"[ANALYTICS] Failed saving block metrics for received block {block.block_index}: {e}")
            
            # Check transaction finality
            for tx in block.transactions:
                tx_hash = self.pow._get_transaction_hash(tx)
                if self.pow.is_transaction_final(tx_hash, self.blocks):
                    print(f"[HANDLE BLOCK] Transaction {tx_hash[:8]}... is now final")
            
            print(f"[HANDLE BLOCK] New block {block.hash} added to chain. Chain length: {len(self.blocks)}, Total work: {self.pow.calculate_chain_work(self.blocks)}")
        else:
            print(f"[HANDLE BLOCK] Block {block.hash} validation failed.")
        
    def _handle_new_transaction(self, transaction_data: Dict[str, Any]) -> None:
        """Handle incoming new transaction."""
        self.pending_transactions.append(transaction_data)
        # Record one new transaction event for TPS
        self.metrics.record_transactions(1)
        
        # Record transaction received time for lifecycle
        try:
            tx_string = json.dumps(transaction_data, sort_keys=True)
            tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
            self.storage.record_tx_received(tx_hash, time.time())
        except Exception as e:
            print(f"[LIFECYCLE] Failed to record tx received: {e}")
        
        print(f"New transaction received: {transaction_data}")
        
    def _handle_network_status(self, status_data: Dict[str, Any]) -> None:
        """Handle network status updates."""
        # Update network hash rate based on network load
        network_load = status_data.get('network_load', 0.5)
        # Estimate hash rate based on network load (simplified model)
        estimated_hash_rate = 1000 + (network_load * 5000)  # 1000-6000 H/s range
        self.pow.update_network_hash_rate(estimated_hash_rate)
        
    def _handle_miner_status(self, status_data: Dict[str, Any]) -> None:
        """Handle miner status updates."""
        # Update network hash rate based on reported mining activity
        if 'hash_rate' in status_data:
            self.pow.update_network_hash_rate(status_data['hash_rate'])
        if 'difficulty' in status_data:
            # Update difficulty if it's different (for network synchronization)
            if status_data['difficulty'] != self.pow.difficulty:
                print(f"[MINER STATUS] Network difficulty updated: {self.pow.difficulty} -> {status_data['difficulty']}")
                self.pow.difficulty = status_data['difficulty']
                
    def _handle_incoming_metrics(self, metrics_data: dict) -> None:
        """Handle incoming metrics from any node and record them."""
        node_id = metrics_data.get('node_id')
        if node_id:
            self.metrics.record_node_metrics(node_id, metrics_data)
            print(f"[METRICS] Node {self.node_id} received metrics from {node_id}. Timestamp: {metrics_data.get('timestamp', 'N/A')}")
            # Add metrics as a transaction
            tx = {
                "type": "metrics",
                "node_id": node_id,
                "metrics": metrics_data,
                "timestamp": metrics_data.get("timestamp", time.time())
            }
            self.pending_transactions.append(tx)
            # Record one new transaction event for TPS
            self.metrics.record_transactions(1)
            # Record transaction received lifecycle for metrics-derived transactions
            try:
                tx_string = json.dumps(tx, sort_keys=True)
                tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
                self.storage.record_tx_received(tx_hash, time.time())
            except Exception as e:
                print(f"[LIFECYCLE] Failed to record metrics tx received: {e}")
            # Update difficulty based on recent block times (PoW equivalent)
            if len(self.blocks) > 10:
                recent_block_times = []
                for i in range(1, min(11, len(self.blocks))):
                    block_time = self.blocks[-i].timestamp - self.blocks[-(i+1)].timestamp
                    recent_block_times.append(block_time)
                self.pow.adjust_difficulty(recent_block_times)
        
    async def _generate_test_transactions(self):
        """Generate test transactions to simulate real blockchain activity."""
        import random
        
        # Generate a test transaction every 30 seconds with 20% probability
        if random.random() < 0.2:  # 20% chance
            # Create a simple transfer transaction
            test_transaction = {
                "type": "transfer",
                "sender": f"pi_node_{random.randint(1, 6)}",
                "recipient": f"pi_node_{random.randint(1, 6)}",
                "amount": round(random.uniform(1.0, 100.0), 2),
                "timestamp": time.time(),
                "description": "Test transaction"
            }
            
            # Add to pending transactions
            self.pending_transactions.append(test_transaction)
            print(f"[TEST TX] Generated test transaction: {test_transaction['sender']} -> {test_transaction['recipient']} ({test_transaction['amount']})")
            
            # Publish transaction to network
            self.mqtt_client.publish_transaction(test_transaction)
            
            # Record transaction for metrics
            self.metrics.record_transactions(1)
    
    def _check_system_health(self) -> bool:
        """Check if the system is healthy enough to process blocks."""
        metrics = self.energy_monitor.get_system_metrics()
        
        # Check temperature
        if metrics['temperature'] > RASPBERRY_PI_SETTINGS['cpu_throttle_temp']:
            print(f"[HEALTH CHECK] System temperature too high: {metrics['temperature']}°C")
            return False
            
        # Check CPU usage
        if metrics['cpu_percent'] > RASPBERRY_PI_SETTINGS['max_cpu_usage']:
            print(f"[HEALTH CHECK] CPU usage too high: {metrics['cpu_percent']:.2f}%")
            return False
            
        # Check memory usage
        if metrics['memory_percent'] > RASPBERRY_PI_SETTINGS['max_memory_usage']:
            print(f"[HEALTH CHECK] Memory usage too high: {metrics['memory_percent']:.2f}%")
            return False
            
        print(f"[HEALTH CHECK] System is healthy. CPU: {metrics['cpu_percent']:.2f}%, Mem: {metrics['memory_percent']:.2f}%, Temp: {metrics['temperature']}°C")
        return True
        
    async def _synchronize_chain(self) -> None:
        """Synchronize the local blockchain with peer nodes."""
        print("Starting chain synchronization...")
        local_chain_length = len(self.blocks)
        print(f"Local chain length: {local_chain_length}, Latest hash: {self.blocks[-1].hash if self.blocks else 'None'}")
        
        # Get peer nodes from configuration
        peers = [node for node in RASPBERRY_PI_NODES if node['id'] != self.node_id]
        print(f"Found {len(peers)} peer nodes to sync with")
        
        for peer in peers:
            try:
                print(f"Attempting to sync with peer: {peer['id']} at {peer['ip']}:{peer['dashboard_port']}")
                await self._sync_with_peer(peer, local_chain_length)
            except Exception as e:
                print(f"Error querying peer {peer['id']}: {e}")
        
        print("Chain synchronization complete")
        # Update difficulty after synchronization
        if len(self.blocks) > 10:
            recent_block_times = []
            for i in range(1, min(11, len(self.blocks))):
                block_time = self.blocks[-i].timestamp - self.blocks[-(i+1)].timestamp
                recent_block_times.append(block_time)
            self.pow.adjust_difficulty(recent_block_times)
        print("Difficulty updated after chain synchronization.")
        
    async def _sync_with_peer(self, peer: Dict[str, Any], local_chain_length: int) -> None:
        """Synchronize with a specific peer node."""
        try:
            peer_url = f"http://{peer['ip']}:{peer['dashboard_port']}/api/blocks"
            params = {'start_index': local_chain_length, 'end_index': -1}
            
            print(f"[SYNC] Requesting blocks from {peer['id']} at {peer_url}")
            response = await self.http_client.get(peer_url, params=params)
            
            if response.status_code == 200:
                blocks_data = response.json()
                print(f"[SYNC] Received {len(blocks_data)} blocks from {peer['id']}")
                
                if blocks_data:
                    # Get all blocks from peer and add to storage
                    all_blocks = []
                    for block_data in blocks_data:
                        try:
                            block = Block.from_dict(block_data)
                            all_blocks.append(block)
                            # Save all blocks to storage for fork resolution
                            self.storage.save_block(block)
                        except Exception as e:
                            print(f"[SYNC] Error processing block from {peer['id']}: {e}")
                            continue
                    
                    # Resolve forks and get the best chain
                    best_chain = self.pow.resolve_forks(all_blocks)
                    
                    # Update local chain if we found a better one
                    if len(best_chain) > len(self.blocks) or self.pow.calculate_chain_work(best_chain) > self.pow.calculate_chain_work(self.blocks):
                        print(f"[SYNC] Switching to better chain from {peer['id']}: {len(best_chain)} blocks with {self.pow.calculate_chain_work(best_chain)} work")
                        self.blocks = best_chain
                    else:
                        print(f"[SYNC] Local chain is better: {len(self.blocks)} blocks with {self.pow.calculate_chain_work(self.blocks)} work")
                    
                    print(f"[SYNC] Sync with {peer['id']} complete. Final chain length: {len(self.blocks)}")
                else:
                    print(f"[SYNC] No new blocks from {peer['id']}")
            else:
                print(f"[SYNC] Failed to get blocks from {peer['id']}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"[SYNC] Error syncing with {peer['id']}: {e}")
            
    async def start(self) -> None:
        """Start the blockchain node operations."""
        print(f"Blockchain node {self.node_id} started")
        
        # Start dashboard in a separate thread
        self.dashboard_thread.start()
        
        # Connect to MQTT broker
        print(f"[DEBUG] Attempting to connect to MQTT brokers...")
        print(f"[DEBUG] MQTT client object: {self.mqtt_client}")
        print(f"[DEBUG] MQTT client type: {type(self.mqtt_client)}")
        connection_result = self.mqtt_client.connect()
        print(f"[DEBUG] Connection result: {connection_result}")
        if not connection_result:
            print(f"[ERROR] Failed to connect to MQTT broker for node {self.node_id}")
        else:
            print(f"[DEBUG] Successfully connected to MQTT broker for node {self.node_id}")
            # Show which broker we're connected to
            network_status = self.mqtt_client.get_network_status()
            print(f"[DEBUG] Connected to broker: {network_status['active_broker']}")
        
        # Perform initial chain synchronization
        print("Performing initial chain synchronization...")
        await self._synchronize_chain()

        # Start periodic tasks
        self.periodic_tasks = [
            asyncio.create_task(self._publish_metrics_periodically()),
            asyncio.create_task(self._process_transactions_periodically()),
            asyncio.create_task(self._synchronize_chain_periodically())
        ]
        await asyncio.gather(*self.periodic_tasks)

    # Publish system metrics
    async def _publish_metrics_periodically(self):
        """Publish system metrics periodically."""
        while True:
            try:
                # Get system metrics
                system_metrics = self.energy_monitor.get_system_metrics()
                
                # Prepare metrics data
                metrics_to_publish = {
                    'node_id': self.node_id,
                    'timestamp': time.time(),
                    'cpu_percent': system_metrics['cpu_percent'],
                    'memory_percent': system_metrics['memory_percent'],
                    'temperature': system_metrics['temperature'],
                    'power_usage': system_metrics['power_usage'],
                    'block_count': len(self.blocks),
                    'pending_transactions': len(self.pending_transactions),
                    'hash_rate': self.pow.network_hash_rate,
                    'difficulty': self.pow.difficulty,
                    'is_mining': self.pow.is_mining_active()
                }
                
                # Record local metrics
                local_metrics_for_record = metrics_to_publish.copy()
                self.metrics.record_node_metrics(self.node_id, local_metrics_for_record)
                
                print(f"[DEBUG] About to publish metrics. MQTT client connected: {self.mqtt_client.connected}")
                print(f"[DEBUG] MQTT client object: {self.mqtt_client}")
                
                # Publish metrics
                self.mqtt_client.publish_metrics(metrics_to_publish)
                print(f"[METRICS] Node {self.node_id} published metrics. Timestamp: {metrics_to_publish['timestamp']}")
                
            except Exception as e:
                print(f"[ERROR] Failed to publish metrics: {e}")
                
            await asyncio.sleep(RASPBERRY_PI_SETTINGS['metrics_interval'])

            # Process pending transactions and create blocks if we're mining
    async def _process_transactions_periodically(self):
        while True:
            # Generate test transactions periodically to simulate real blockchain activity
            await self._generate_test_transactions()
            
            # In PoW, any node can attempt to mine a block
            # Check if enough time has passed since the last block
            previous_block_timestamp = self.blocks[-1].timestamp if self.blocks else 0.0
            previous_block_index = self.blocks[-1].block_index if self.blocks else -1

            # Check if we should attempt mining (any node can mine in PoW)
            current_time = time.time()
            if current_time < previous_block_timestamp + self.pow.target_block_time:
                print(f"[PROCESS TX] Not time to mine yet. Last block: {previous_block_timestamp}, Current: {current_time}")
                await asyncio.sleep(1)
                continue
            
            # Add randomization to prevent all nodes from mining simultaneously
            import random
            mining_delay = random.uniform(0, 0.5)  # Random delay up to 0.5 seconds
            await asyncio.sleep(mining_delay)
            
            print(f"[PROCESS TX] {self.node_id} attempting to mine a block.")

            # Check system health before proposing a block
            if not self._check_system_health():
                print(f"[PROCESS TX] System not healthy for {self.node_id}. Skipping block proposal.")
                await asyncio.sleep(1) # Short delay before re-checking
                continue
            else:
                print(f"[PROCESS TX] System health check passed for {self.node_id}.")

            # Check if enough time has passed since the last block
            if current_time < previous_block_timestamp + self.pow.target_block_time:
                print(f"[PROCESS TX] Not time to mine a block yet. Last block time: {previous_block_timestamp}, Current time: {current_time}")
                await asyncio.sleep(1) # Wait a bit before next attempt
                continue
            else:
                print(f"[PROCESS TX] Time to mine a block for {self.node_id}.")

            # In PoW, we can mine blocks even without transactions (like Bitcoin)
            # This ensures continuous block production and network security
            start_time = time.time()
            
            # Prepare block data for mining
            transactions_to_include = self.pending_transactions[:10] if self.pending_transactions else []
            
            if self.pending_transactions:
                print(f"[PROCESS TX] {len(self.pending_transactions)} pending transactions found.")
            else:
                print(f"[PROCESS TX] No pending transactions, mining empty block.")
            
            block_data = {
                'block_index': len(self.blocks),
                'timestamp': time.time(),
                'transactions': transactions_to_include,
                'previous_hash': self.blocks[-1].hash if self.blocks else "0" * 64,
                'miner': self.node_id,
                'energy_metrics': self.energy_monitor.get_system_metrics()
            }
            
            # Mine the block using PoW
            new_block = self.pow.mine_block(block_data, max_time=30.0)  # 30 second mining timeout
            
            if not new_block:
                print(f"[PROCESS TX] Mining failed or timed out for {self.node_id}")
                await asyncio.sleep(1)
                continue

            print(f"[PROCESS TX] New block created with index {new_block.block_index} and hash {new_block.hash}.")
            print(f"[PROCESS TX] Block miner: {new_block.miner}")
            print(f"[PROCESS TX] Current node: {self.node_id}")

            # Record propagation delay
            self.metrics.record_propagation_delay(time.time() - start_time)

            # Publish new block
            self.mqtt_client.publish_block(new_block.to_dict())
            print(f"[PROCESS TX] Node {self.node_id} published new block: {new_block.hash}")

            # Add block to local chain and save to storage
            self.blocks.append(new_block)
            self.storage.save_block(new_block)
            # Persist per-block analytics
            try:
                interval = new_block.timestamp - previous_block_timestamp
                consensus_time = new_block.energy_metrics.get('consensus_time', 0)
                power_usage = new_block.energy_metrics.get('power_usage', 0)
                self.storage.save_block_metrics(new_block.block_index, new_block.timestamp, interval, consensus_time, power_usage)
            except Exception as e:
                print(f"[ANALYTICS] Failed saving block metrics for local block {new_block.block_index}: {e}")
            print(f"[PROCESS TX] Block {new_block.hash} added to local chain and saved.")

            # Record metrics for charts
            self.metrics.record_block_time(new_block.timestamp - previous_block_timestamp)
            self.metrics.record_consensus_time(new_block.energy_metrics.get('consensus_time', 0))

            # Publish mining status
            self.mqtt_client.publish_miner_status({
                'node_id': self.node_id,
                'block_count': len(self.blocks),
                'hash_rate': self.pow.network_hash_rate,
                'difficulty': self.pow.difficulty,
                'mining_time': new_block.energy_metrics.get('mining_time', 0)
            })

            # Clear processed transactions (only if there were any)
            if self.pending_transactions:
                self.pending_transactions = self.pending_transactions[10:]
            await asyncio.sleep(1) # Check frequently

    async def _synchronize_chain_periodically(self):
        """Periodically synchronize the local blockchain with peer nodes."""
        while True:
            await self._synchronize_chain()
            await asyncio.sleep(RASPBERRY_PI_SETTINGS['sync_interval'])

if __name__ == "__main__":
    node = BlockchainNode()
    asyncio.run(node.start())  # Use asyncio.run to execute the coroutine