from collections import defaultdict, deque
import time
from storage.sqlite_storage import SQLiteStorage
from consensus.block import Block
from typing import Any, Dict, List, Optional
import psutil
import threading
from contextlib import contextmanager

class BlockchainMetrics:
    def __init__(self, local_node_id: str, storage: SQLiteStorage):
        self.metrics = {}
        self.tps_history = []
        self.consensus_time_history = []
        self.block_time_history = []
        self.cpu_history = []
        self.memory_history = []
        self.power_usage_history = []
        
        self.local_node_id = local_node_id
        self.storage = storage
        
        # Rolling window of transaction timestamps (seconds)
        self.transaction_events: deque[float] = deque()
        self.tps_window_seconds: int = 10
        
        # New: Store metrics for all nodes
        self.all_nodes_metrics = defaultdict(lambda: {
            'cpu_percent': 0,
            'memory_percent': 0,
            'temperature': 0,
            'power_usage': 0,
            'block_count': 0,
            'pending_transactions': 0,
            'hash_rate': 0,  # PoW: hash rate instead of stake
            'is_mining': False,  # PoW: mining status
            'timestamp': 0
        })
        self.current_difficulty = 1  # PoW: current mining difficulty

        # Resource and operation metrics (IoT-DPoS parity)
        self.resource_metrics_history: deque = deque(maxlen=100)
        self.operation_metrics: Dict[str, List[Dict[str, Any]]] = {
            'block_validation': [],
            'block_creation': [],
            'network_operations': [],
            'database_operations': []
        }
        self._op_lock = threading.Lock()

    @contextmanager
    def monitor_operation(self, operation_type: str, operation_id: Optional[str] = None):
        """Context manager to record resource usage around an operation."""
        start_time = time.time()
        cpu_initial = psutil.cpu_percent(interval=None)
        mem_info_initial = psutil.virtual_memory()
        net_initial = psutil.net_io_counters()
        error: Optional[str] = None
        try:
            yield
        except Exception as e:
            error = str(e)
            raise
        finally:
            end_time = time.time()
            duration = max(0.0, end_time - start_time)
            cpu_final = psutil.cpu_percent(interval=None)
            # Approximate average as mean of initial and final samples
            cpu_avg = (cpu_initial + cpu_final) / 2.0
            mem_info_final = psutil.virtual_memory()
            memory_initial_mb = mem_info_initial.used / (1024 * 1024)
            memory_final_mb = mem_info_final.used / (1024 * 1024)
            memory_delta_mb = memory_final_mb - memory_initial_mb
            net_final = psutil.net_io_counters()
            record = {
                'operation_id': operation_id or f"{operation_type}-{int(start_time*1000)}",
                'operation_type': operation_type,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'cpu_usage': {
                    'initial': cpu_initial,
                    'final': cpu_final,
                    'avg': cpu_avg
                },
                'memory_usage': {
                    'initial_mb': memory_initial_mb,
                    'final_mb': memory_final_mb,
                    'memory_delta_mb': memory_delta_mb
                },
                'network_usage': {
                    'bytes_sent': max(0, net_final.bytes_sent - net_initial.bytes_sent),
                    'bytes_recv': max(0, net_final.bytes_recv - net_initial.bytes_recv),
                    'packets_sent': max(0, net_final.packets_sent - net_initial.packets_sent),
                    'packets_recv': max(0, net_final.packets_recv - net_initial.packets_recv)
                },
                'error': error
            }
            with self._op_lock:
                self.resource_metrics_history.append(record)
                if operation_type in self.operation_metrics:
                    self.operation_metrics[operation_type].append(record)
                else:
                    # Allow ad-hoc operation types
                    self.operation_metrics.setdefault(operation_type, []).append(record)

    def record_network_operation(self, operation: str, bytes_transferred: int, duration: float, success: bool = True):
        throughput_mbps = 0.0
        if duration > 0:
            throughput_mbps = (bytes_transferred * 8) / (duration * 1_000_000)
        entry = {
            'operation': operation,
            'timestamp': time.time(),
            'bytes_transferred': int(bytes_transferred),
            'duration': float(duration),
            'success': bool(success),
            'throughput_mbps': throughput_mbps
        }
        with self._op_lock:
            self.operation_metrics['network_operations'].append(entry)

    def record_database_operation(self, operation: str, duration: float, rows_affected: int = 0):
        throughput = 0.0
        if duration > 0:
            throughput = rows_affected / duration
        entry = {
            'operation': operation,
            'timestamp': time.time(),
            'duration': float(duration),
            'rows_affected': int(rows_affected),
            'throughput_rows_per_sec': throughput
        }
        with self._op_lock:
            self.operation_metrics['database_operations'].append(entry)

    def get_resource_metrics(self) -> Dict[str, Any]:
        """Return recent operation records and per-type summaries plus current system state."""
        recent_ops = list(self.resource_metrics_history)

        def summarize_block_ops(op_type: str) -> Dict[str, Any]:
            ops = self.operation_metrics.get(op_type, [])
            if not ops:
                return {'count': 0, 'avg_duration': 0.0, 'avg_cpu': 0.0, 'avg_memory_delta': 0.0, 'total_network_bytes': 0}
            count = len(ops)
            avg_duration = sum(o.get('duration', 0.0) for o in ops) / count
            avg_cpu = sum((o.get('cpu_usage', {}).get('avg', 0.0) for o in ops)) / count
            avg_memory_delta = sum((o.get('memory_usage', {}).get('memory_delta_mb', 0.0) for o in ops)) / count
            total_network_bytes = sum((o.get('network_usage', {}).get('bytes_sent', 0) + o.get('network_usage', {}).get('bytes_recv', 0) for o in ops))
            return {
                'count': count,
                'avg_duration': avg_duration,
                'avg_cpu': avg_cpu,
                'avg_memory_delta': avg_memory_delta,
                'total_network_bytes': total_network_bytes
            }

        net_ops = self.operation_metrics.get('network_operations', [])
        db_ops = self.operation_metrics.get('database_operations', [])
        net_summary = {
            'count': len(net_ops),
            'avg_duration': (sum(o.get('duration', 0.0) for o in net_ops) / len(net_ops)) if net_ops else 0.0,
            'total_bytes_transferred': sum(o.get('bytes_transferred', 0) for o in net_ops),
            'avg_throughput_mbps': (sum(o.get('throughput_mbps', 0.0) for o in net_ops) / len(net_ops)) if net_ops else 0.0
        }
        db_summary = {
            'count': len(db_ops),
            'avg_duration': (sum(o.get('duration', 0.0) for o in db_ops) / len(db_ops)) if db_ops else 0.0,
            'total_rows_affected': sum(o.get('rows_affected', 0) for o in db_ops),
            'avg_throughput_rows_per_sec': (sum(o.get('throughput_rows_per_sec', 0.0) for o in db_ops) / len(db_ops)) if db_ops else 0.0
        }

        vm = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        current_state = {
            'cpu_percent': psutil.cpu_percent(interval=None),
            'memory_percent': vm.percent,
            'memory_available_mb': vm.available / (1024 * 1024),
            'disk_usage_percent': disk.percent,
            'network_io': {
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
                'packets_sent': net.packets_sent,
                'packets_recv': net.packets_recv
            }
        }

        return {
            'recent_operations': recent_ops,
            'operation_summaries': {
                'block_validation': summarize_block_ops('block_validation'),
                'block_creation': summarize_block_ops('block_creation'),
                'network_operations': net_summary,
                'database_operations': db_summary
            },
            'current_system_state': current_state
        }

    def get_operation_metrics(self, operation_type: Optional[str] = None):
        if operation_type:
            return self.operation_metrics.get(operation_type, [])
        return self.operation_metrics

    def record_block_time(self, value):
        self.block_time_history.append(value)
        if len(self.block_time_history) > 20: # Keep last 20 for chart
            self.block_time_history.pop(0)

    def record_consensus_time(self, value):
        self.consensus_time_history.append(value)
        if len(self.consensus_time_history) > 20:
            self.consensus_time_history.pop(0)

    def record_transactions(self, count):
        """Record 'count' new transactions at the current timestamp for TPS calculation."""
        now = time.time()
        for _ in range(max(0, int(count))):
            self.transaction_events.append(now)
        # Drop events older than the window
        cutoff = now - self.tps_window_seconds
        while self.transaction_events and self.transaction_events[0] < cutoff:
            self.transaction_events.popleft()

    def record_propagation_delay(self, value):
        # For future use or specific tracking
        pass

    def record_node_metrics(self, node_id: str, metrics_data: dict):
        """Record and update metrics for a specific node."""
        self.all_nodes_metrics[node_id].update({
            'cpu_percent': metrics_data.get('cpu_percent', 0),
            'memory_percent': metrics_data.get('memory_percent', 0),
            'temperature': metrics_data.get('temperature', 0),
            'power_usage': metrics_data.get('power_usage', 0),
            'block_count': metrics_data.get('block_count', 0),
            'pending_transactions': metrics_data.get('pending_transactions', 0),
            'hash_rate': metrics_data.get('hash_rate', 0),  # PoW: hash rate
            'is_mining': metrics_data.get('is_mining', False),  # PoW: mining status
            'timestamp': time.time() # Timestamp of last update
        })
        
        # Update current difficulty
        if 'difficulty' in metrics_data:
            self.current_difficulty = metrics_data['difficulty']

    def get_system_metrics(self) -> dict:
        # This now returns a dict of all nodes' system metrics
        return {
            node_id: {
                'cpu_percent': data['cpu_percent'],
                'memory_percent': data['memory_percent'],
                'temperature': data['temperature'],
                'power_usage': data['power_usage'],
                'block_count': data.get('block_count', 0),  # Include block count
                'pending_transactions': data.get('pending_transactions', 0),  # Include pending transactions
                'is_mining': data.get('is_mining', False),  # Include mining status
                'timestamp': data['timestamp']
            } for node_id, data in self.all_nodes_metrics.items()
        }

    def get_cumulative_mining_power(self) -> float:
        """Calculate cumulative energy used for mining from genesis to current block."""
        # Get all blocks from storage
        total_blocks = self.get_chain_length()
        if total_blocks == 0:
            return 0.0
        
        # Get blocks from storage to calculate actual cumulative energy
        blocks = self.storage.get_blocks(0, total_blocks - 1)
        cumulative_energy = 0.0
        
        for block in blocks:
            # Extract energy per block from block's energy metrics
            if hasattr(block, 'energy_metrics') and block.energy_metrics:
                # Use energy_per_block if available, otherwise calculate from power_usage and mining_time
                if 'energy_per_block' in block.energy_metrics:
                    energy_per_block = block.energy_metrics.get('energy_per_block', 0.0)
                    cumulative_energy += energy_per_block
                elif 'power_usage' in block.energy_metrics and 'mining_time' in block.energy_metrics:
                    power_usage = block.energy_metrics.get('power_usage', 1.0)
                    mining_time = block.energy_metrics.get('mining_time', 0.0)
                    energy_per_block = power_usage * mining_time
                    cumulative_energy += energy_per_block
                else:
                    # Fallback to estimated energy per block (1W * 3 seconds = 3W)
                    cumulative_energy += 3.0
        
        return cumulative_energy

    def get_network_total_energy(self) -> float:
        """Calculate total energy used across the entire network by aggregating from all nodes."""
        import httpx
        import asyncio
        from config.network_config import RASPBERRY_PI_NODES
        
        total_network_energy = 0.0
        node_energies = {}
        
        # Get energy from local node
        local_energy = self.get_cumulative_mining_power()
        total_network_energy += local_energy
        node_energies[self.local_node_id] = local_energy
        
        # Get energy from all other nodes
        for node in RASPBERRY_PI_NODES:
            if node['id'] == self.local_node_id:
                continue  # Skip local node
                
            try:
                # Query each node's API for their cumulative energy
                url = f"http://{node['ip']}:{node['dashboard_port']}/api/energy"
                response = httpx.get(url, timeout=5.0)
                
                if response.status_code == 200:
                    energy_data = response.json()
                    node_energy = energy_data.get('cumulative_energy', 0.0)
                    total_network_energy += node_energy
                    node_energies[node['id']] = node_energy
                    print(f"[ENERGY] {node['id']}: {node_energy:.2f} watt-seconds")
                else:
                    print(f"[ENERGY] Failed to get energy from {node['id']}: HTTP {response.status_code}")
                    node_energies[node['id']] = 0.0
                    
            except Exception as e:
                print(f"[ENERGY] Error getting energy from {node['id']}: {e}")
                node_energies[node['id']] = 0.0
        
        print(f"[ENERGY] Network total: {total_network_energy:.2f} watt-seconds")
        print(f"[ENERGY] Node breakdown: {node_energies}")
        
        return total_network_energy

    def get_power_metrics(self) -> dict:
        # Return network-wide cumulative mining power
        try:
            network_total_energy = self.get_network_total_energy()
            return {"total_power": network_total_energy}
        except Exception as e:
            print(f"[POWER METRICS] Error getting network energy, falling back to local: {e}")
            # Fallback to local energy if network aggregation fails
            local_energy = self.get_cumulative_mining_power()
            return {"total_power": local_energy}

    def get_blockchain_metrics(self) -> dict:
        # This will be refined, currently mostly local node's perspective
        total_blocks = self.get_chain_length()
        return {
            "tps": self.get_tps(),
            "consensus_time_avg": sum(self.consensus_time_history) / len(self.consensus_time_history) if self.consensus_time_history else 0,
            "block_time_avg": sum(self.block_time_history) / len(self.block_time_history) if self.block_time_history else 0,
            "total_blocks": total_blocks,  # Updated to use get_chain_length
            "confirmation_blocks": 6,  # Bitcoin-style confirmation requirement
            "max_block_size": 1024 * 1024  # 1MB block size limit
        }

    def get_blockchain_size(self) -> int:
        """Return a proxy for the total blockchain size (e.g., total blocks * average block size)."""
        # This is a rough estimation. A more accurate size would involve serializing and measuring actual blocks.
        total_blocks = self.get_chain_length()
        # Assuming an average block size of 1KB (1024 bytes) as a rough estimate
        # In a real scenario, you'd calculate actual block sizes or store them.
        approx_block_size_bytes = 1024 
        return total_blocks * approx_block_size_bytes # Updated to use total_blocks from get_chain_length

    def get_all_miners_metrics(self) -> dict:
        """Return the current view of all nodes and their hash rates."""
        return {
            node_id: data.get('hash_rate', 0) 
            for node_id, data in self.all_nodes_metrics.items()
        }

    def get_current_difficulty(self) -> int:
        """Return the current mining difficulty."""
        return self.current_difficulty

    def get_tps(self) -> float:
        """Compute transactions per second across all nodes over the rolling window."""
        now = time.time()
        cutoff = now - self.tps_window_seconds
        # Trim old events
        while self.transaction_events and self.transaction_events[0] < cutoff:
            self.transaction_events.popleft()
        if not self.transaction_events:
            return 0.0
        window_span = max(1e-6, min(self.tps_window_seconds, (self.transaction_events[-1] - self.transaction_events[0]) or self.tps_window_seconds))
        return len(self.transaction_events) / window_span

    def get_chain_length(self) -> int:
        """Return the current length of the blockchain from storage."""
        return self.storage.get_chain_length()

    def get_latest_block_hash(self) -> str | None:
        """Return the hash of the latest block from storage."""
        latest_block = self.storage.get_latest_block()
        return latest_block.hash if latest_block else None

    def get_blocks_from_storage(self, start_block_index: int, end_block_index: int) -> list:
        """Retrieve a range of blocks from storage."""
        return self.storage.get_blocks(start_block_index, end_block_index)
    
    def get_chain_work(self) -> int:
        """Calculate total proof-of-work for the current chain."""
        blocks = self.storage.get_blocks()
        total_work = 0
        for block in blocks:
            difficulty = block.energy_metrics.get('difficulty', 1)
            total_work += difficulty
        return total_work
    
    def get_orphan_blocks_count(self) -> int:
        """Get the number of orphan blocks currently stored."""
        # This would need to be implemented in the PoW consensus class
        # For now, return 0 as a placeholder
        return 0 