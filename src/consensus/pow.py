import hashlib
import time
import json
import threading
from typing import Dict, Any, Optional, List, Set
from .block import Block
from monitoring.metrics import BlockchainMetrics

class ProofOfWork:
    def __init__(self, target_block_time: float = 3.0, metrics: Optional[BlockchainMetrics] = None):
        # PoW Configuration
        self.target_block_time = target_block_time  # Target block time in seconds
        self.difficulty = 1  # Initial mining difficulty
        self.max_difficulty = 2**32  # Maximum difficulty
        self.min_difficulty = 1  # Minimum difficulty
        
        # Mining parameters
        self.nonce = 0
        self.max_nonce = 2**32 - 1
        self.mining_thread = None
        self.is_mining = False
        
        # Energy and performance tracking
        self.energy_threshold = 5.0  # Maximum energy usage threshold (watts)
        self.metrics = metrics
        
        # Network hash rate tracking
        self.network_hash_rate = 1000  # Initial hash rate (hashes per second)
        self.last_difficulty_adjustment = time.time()
        self.difficulty_adjustment_interval = 2016  # Adjust difficulty every 2016 blocks (like Bitcoin)
        
        # Block time tracking for difficulty adjustment
        self.recent_block_times = []
        self.max_block_times_history = 2016
        
        # Mining statistics
        self.total_blocks_mined = 0
        self.total_mining_time = 0
        self.total_energy_consumed = 0
        
        # Bitcoin-style consensus rules
        self.max_block_size = 1024 * 1024  # 1MB block size limit (like Bitcoin)
        self.confirmation_blocks = 6  # Number of confirmations for finality (like Bitcoin)
        self.orphan_blocks: Dict[str, Block] = {}  # Store orphaned blocks
        self.pending_blocks: Dict[str, Block] = {}  # Store blocks waiting for parent
        self.chain_tips: Dict[str, Block] = {}  # Multiple chain tips for fork resolution
        
    def calculate_target_difficulty(self) -> int:
        """Calculate the target difficulty based on current network conditions."""
        # Target difficulty is inversely proportional to the difficulty value
        # Lower difficulty = higher target (easier to mine)
        # Higher difficulty = lower target (harder to mine)
        return int(2**256 // self.difficulty)
    
    def calculate_chain_work(self, blocks: List[Block]) -> int:
        """
        Calculate cumulative proof-of-work for a chain.
        This implements the "longest chain rule" based on work, not length.
        """
        total_work = 0
        for block in blocks:
            # Work = 2^256 / (target_difficulty)
            # Target difficulty = 2^256 / difficulty
            # So work = difficulty
            difficulty = block.energy_metrics.get('difficulty', 1)
            total_work += difficulty
        return total_work
    
    def get_best_chain(self, all_blocks: List[Block]) -> List[Block]:
        """
        Find the chain with the most cumulative proof-of-work.
        This implements Bitcoin's longest chain rule.
        """
        if not all_blocks:
            return []
        
        # Group blocks by their chain (using previous_hash links)
        chains = self._build_all_chains(all_blocks)
        
        # Find the chain with the most work
        best_chain = []
        best_work = 0
        
        for chain in chains:
            chain_work = self.calculate_chain_work(chain)
            if chain_work > best_work:
                best_work = chain_work
                best_chain = chain
        
        return best_chain
    
    def _build_all_chains(self, blocks: List[Block]) -> List[List[Block]]:
        """Build all possible chains from the given blocks."""
        # Create a map of block hash to block
        block_map = {block.hash: block for block in blocks}
        
        # Find all chain tips (blocks with no children)
        tips = set(block.hash for block in blocks)
        for block in blocks:
            if block.previous_hash in block_map:
                tips.discard(block.previous_hash)
        
        # Build chains from each tip back to genesis
        chains = []
        for tip_hash in tips:
            chain = []
            current_hash = tip_hash
            
            while current_hash in block_map:
                block = block_map[current_hash]
                chain.append(block)
                current_hash = block.previous_hash
            
            # Reverse to get genesis to tip order
            chain.reverse()
            chains.append(chain)
        
        return chains
    
    def validate_block_size(self, block: Block) -> bool:
        """Validate block size limit (Bitcoin-style consensus rule)."""
        block_size = len(json.dumps(block.to_dict()))
        return block_size <= self.max_block_size
    
    def get_block_confirmations(self, block_hash: str, main_chain: List[Block]) -> int:
        """
        Calculate how many confirmations a block has.
        Returns the number of blocks built on top of this block in the main chain.
        """
        if not main_chain:
            return 0
        
        # Find the block in the main chain
        block_index = -1
        for i, block in enumerate(main_chain):
            if block.hash == block_hash:
                block_index = i
                break
        
        if block_index == -1:
            return 0  # Block not in main chain
        
        # Confirmations = blocks after this block
        return len(main_chain) - block_index - 1
    
    def is_transaction_final(self, tx_hash: str, main_chain: List[Block]) -> bool:
        """
        Check if a transaction is final (has enough confirmations).
        Implements Bitcoin's probabilistic finality.
        """
        # Find the block containing this transaction
        for block in main_chain:
            for tx in block.transactions:
                if self._get_transaction_hash(tx) == tx_hash:
                    confirmations = self.get_block_confirmations(block.hash, main_chain)
                    return confirmations >= self.confirmation_blocks
        
        return False
    
    def _get_transaction_hash(self, transaction: Dict[str, Any]) -> str:
        """Calculate hash of a transaction."""
        tx_string = json.dumps(transaction, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def handle_orphan_block(self, block: Block) -> bool:
        """
        Handle orphan blocks (blocks whose parent we don't have yet).
        Returns True if the block was added to pending blocks.
        """
        # Check if we have the parent block
        parent_exists = any(b.hash == block.previous_hash for b in self.chain_tips.values())
        
        if not parent_exists:
            # Store as orphan block
            self.orphan_blocks[block.hash] = block
            print(f"[PoW] Stored orphan block {block.hash} (parent {block.previous_hash} not found)")
            return True
        
        return False
    
    def process_pending_blocks(self, main_chain: List[Block]) -> List[Block]:
        """
        Process pending blocks that can now be added to the chain.
        Returns updated main chain.
        """
        updated_chain = main_chain.copy()
        processed_blocks = []
        
        # Try to add orphan blocks that now have parents
        orphan_hashes = list(self.orphan_blocks.keys())
        for orphan_hash in orphan_hashes:
            orphan_block = self.orphan_blocks[orphan_hash]
            
            # Check if parent is now in main chain
            parent_in_chain = any(b.hash == orphan_block.previous_hash for b in updated_chain)
            
            if parent_in_chain:
                # Validate the orphan block
                if self.validate_block(orphan_block, 0, 0, 0):
                    # Add to chain
                    updated_chain.append(orphan_block)
                    processed_blocks.append(orphan_block)
                    print(f"[PoW] Added orphan block {orphan_hash} to chain")
                
                # Remove from orphan blocks
                del self.orphan_blocks[orphan_hash]
        
        return updated_chain
    
    def resolve_forks(self, all_blocks: List[Block]) -> List[Block]:
        """
        Resolve forks by choosing the chain with the most proof-of-work.
        Implements Bitcoin's fork resolution mechanism.
        """
        if not all_blocks:
            return []
        
        # Get the best chain (most work)
        best_chain = self.get_best_chain(all_blocks)
        
        # Update chain tips
        self.chain_tips = {}
        for block in all_blocks:
            # Check if this block is a tip (no children)
            is_tip = not any(b.previous_hash == block.hash for b in all_blocks)
            if is_tip:
                self.chain_tips[block.hash] = block
        
        print(f"[PoW] Fork resolution: Best chain has {len(best_chain)} blocks with {self.calculate_chain_work(best_chain)} total work")
        
        return best_chain
    
    def mine_block(self, block_data: Dict[str, Any], max_time: float = 60.0) -> Optional[Block]:
        """
        Mine a new block using Proof of Work.
        
        Args:
            block_data: Block data without nonce and hash
            max_time: Maximum time to spend mining (seconds)
            
        Returns:
            Mined block if successful, None if timeout or interrupted
        """
        if self.is_mining:
            print("[PoW] Already mining, cannot start new mining operation")
            return None
            
        self.is_mining = True
        start_time = time.time()
        target_difficulty = self.calculate_target_difficulty()
        
        print(f"[PoW] Starting mining with difficulty: {self.difficulty}")
        print(f"[PoW] Target difficulty: {target_difficulty}")
        
        # Create block template
        block_template = {
            'block_index': block_data['block_index'],
            'timestamp': block_data['timestamp'],
            'transactions': block_data['transactions'],
            'previous_hash': block_data['previous_hash'],
            'miner': block_data.get('miner', block_data.get('validator', 'unknown')),
            'energy_metrics': block_data['energy_metrics'],
            'difficulty': self.difficulty,
            'nonce': 0
        }
        
        # Mining loop
        for nonce in range(self.max_nonce):
            if not self.is_mining:
                print("[PoW] Mining interrupted")
                return None
                
            # Update nonce in block template
            block_template['nonce'] = nonce
            
            # Calculate block hash
            block_string = json.dumps(block_template, sort_keys=True)
            block_hash = hashlib.sha256(block_string.encode()).hexdigest()
            
            # Convert hash to integer for comparison
            hash_int = int(block_hash, 16)
            
            # Check if hash meets target difficulty
            if hash_int < target_difficulty:
                mining_time = time.time() - start_time
                self.is_mining = False
                
                # Calculate power usage during mining
                # Use the mathematical model: Eblock = power_draw × E[Tblock]
                power_draw = block_template['energy_metrics'].get('power_usage', 1.0)  # Default 1W
                expected_block_time = self.calculate_expected_block_time()
                energy_per_block = self.calculate_energy_per_block(power_draw, expected_block_time)
                
                # Create the mined block
                mined_block = Block(
                    block_index=block_template['block_index'],
                    timestamp=block_template['timestamp'],
                    transactions=block_template['transactions'],
                    previous_hash=block_template['previous_hash'],
                    miner=block_template['miner'],
                    energy_metrics={
                        **block_template['energy_metrics'],
                        'mining_time': mining_time,
                        'difficulty': self.difficulty,
                        'nonce': nonce,
                        'hash_rate': self.network_hash_rate,
                        'power_usage': power_draw,  # Power draw during mining
                        'energy_per_block': energy_per_block,  # Energy consumed for this block
                        'expected_block_time': expected_block_time
                    }
                )
                
                # Validate block size (Bitcoin consensus rule)
                if not self.validate_block_size(mined_block):
                    print(f"[PoW] Block size {len(json.dumps(mined_block.to_dict()))} exceeds limit {self.max_block_size}")
                    self.is_mining = False
                    return None
                
                # Update mining statistics
                self.total_blocks_mined += 1
                self.total_mining_time += mining_time
                
                print(f"[PoW] Block mined successfully!")
                print(f"[PoW] Hash: {block_hash}")
                print(f"[PoW] Nonce: {nonce}")
                print(f"[PoW] Mining time: {mining_time:.2f} seconds")
                print(f"[PoW] Difficulty: {self.difficulty}")
                print(f"[PoW] Block size: {len(json.dumps(mined_block.to_dict()))} bytes")
                
                return mined_block
            
            # Check timeout
            if time.time() - start_time > max_time:
                print(f"[PoW] Mining timeout after {max_time} seconds")
                self.is_mining = False
                return None
        
        print("[PoW] Exhausted all nonce values")
        self.is_mining = False
        return None
    
    def validate_block(self, block: Block, power_usage: float, previous_block_timestamp: float, previous_block_index: int, sync_tolerance: float = 0.0) -> bool:
        """
        Validate a block based on PoW rules and energy efficiency.
        
        Args:
            block: Block to validate
            power_usage: Current power usage
            previous_block_timestamp: Timestamp of previous block
            previous_block_index: Index of previous block
            sync_tolerance: Time tolerance for synchronization
            
        Returns:
            True if block is valid, False otherwise
        """
        print(f"[PoW VALIDATE] Validating block {block.block_index}")
        
        # Check if block_index is greater than previous block_index
        if block.block_index <= previous_block_index:
            print(f"[PoW VALIDATE] Block index {block.block_index} is not greater than previous {previous_block_index}")
            return False
        
        # Check if block timestamp is greater than previous block timestamp
        if block.timestamp <= previous_block_timestamp - sync_tolerance:
            print(f"[PoW VALIDATE] Block timestamp {block.timestamp} is not greater than previous {previous_block_timestamp}")
            return False
        
        # Validate block size (Bitcoin consensus rule)
        if not self.validate_block_size(block):
            print(f"[PoW VALIDATE] Block size exceeds limit")
            return False
        
        # Validate PoW hash
        if not self._validate_proof_of_work(block):
            print("[PoW VALIDATE] Proof of work validation failed")
            return False
        
        # Check energy efficiency
        if power_usage > self.energy_threshold:
            print(f"[PoW VALIDATE] Energy usage {power_usage}W exceeds threshold {self.energy_threshold}W")
            return False
        
        # Check if block was created within reasonable time window
        current_time = time.time()
        if abs(current_time - block.timestamp) > self.target_block_time * 10:  # Allow 10x target time for network propagation
            print(f"[PoW VALIDATE] Block timestamp {block.timestamp} is too far from current time {current_time}")
            return False
        
        print(f"[PoW VALIDATE] Block {block.block_index} validation successful")
        return True
    
    def _validate_proof_of_work(self, block: Block) -> bool:
        """Validate the proof of work for a block."""
        # Reconstruct block data for hash calculation
        block_data = {
            'block_index': block.block_index,
            'timestamp': block.timestamp,
            'transactions': block.transactions,
            'previous_hash': block.previous_hash,
            'miner': block.miner,
            'energy_metrics': block.energy_metrics,
            'difficulty': block.energy_metrics.get('difficulty', self.difficulty),
            'nonce': block.energy_metrics.get('nonce', 0)
        }
        
        # Calculate hash
        block_string = json.dumps(block_data, sort_keys=True)
        calculated_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        # Verify hash matches
        if calculated_hash != block.hash:
            print(f"[PoW VALIDATE] Hash mismatch: calculated={calculated_hash}, block={block.hash}")
            return False
        
        # Verify hash meets target difficulty
        target_difficulty = self.calculate_target_difficulty()
        hash_int = int(calculated_hash, 16)
        
        if hash_int >= target_difficulty:
            print(f"[PoW VALIDATE] Hash {calculated_hash} does not meet target difficulty")
            return False
        
        return True
    
    def adjust_difficulty(self, recent_block_times: List[float]) -> None:
        """
        Adjust mining difficulty based on recent block times.
        
        Args:
            recent_block_times: List of recent block intervals
        """
        if len(recent_block_times) < 10:  # Need at least 10 blocks for adjustment
            return
        
        # Calculate average block time
        avg_block_time = sum(recent_block_times) / len(recent_block_times)
        
        # Adjust difficulty based on target block time
        if avg_block_time > self.target_block_time * 1.1:  # Too slow
            self.difficulty = max(self.min_difficulty, int(self.difficulty * 0.9))
            print(f"[PoW] Decreasing difficulty to {self.difficulty} (avg block time: {avg_block_time:.2f}s)")
        elif avg_block_time < self.target_block_time * 0.9:  # Too fast
            self.difficulty = min(self.max_difficulty, int(self.difficulty * 1.1))
            print(f"[PoW] Increasing difficulty to {self.difficulty} (avg block time: {avg_block_time:.2f}s)")
        else:
            print(f"[PoW] Difficulty unchanged at {self.difficulty} (avg block time: {avg_block_time:.2f}s)")
    
    def update_network_hash_rate(self, new_hash_rate: float) -> None:
        """Update the network hash rate estimate."""
        self.network_hash_rate = new_hash_rate
        print(f"[PoW] Updated network hash rate to {new_hash_rate} H/s")
    
    def calculate_expected_block_time(self) -> float:
        """
        Calculate expected block time using the model: E[Tblock] = (difficulty × 2^32) / hash_rate
        """
        if self.network_hash_rate <= 0:
            return float('inf')
        
        expected_time = (self.difficulty * 2**32) / self.network_hash_rate
        return expected_time
    
    def calculate_transaction_throughput(self, tx_per_block: int, tx_arrival_rate: float) -> float:
        """
        Calculate transaction throughput using the model: TPS = min(tx_per_block / E[Tblock], tx_arrival_rate)
        """
        expected_block_time = self.calculate_expected_block_time()
        if expected_block_time <= 0:
            return 0
        
        tps_from_blocks = tx_per_block / expected_block_time
        return min(tps_from_blocks, tx_arrival_rate)
    
    def calculate_energy_per_block(self, power_draw: float) -> float:
        """
        Calculate energy per block using the model: Eblock = power_draw × E[Tblock]
        """
        expected_block_time = self.calculate_expected_block_time()
        return power_draw * expected_block_time
    
    def calculate_total_energy(self, power_draw: float, num_blocks: int) -> float:
        """
        Calculate total energy over k blocks using the model: Etotal = Σ (from i=1 to k) Eblock_i
        """
        energy_per_block = self.calculate_energy_per_block(power_draw)
        return energy_per_block * num_blocks
    
    def stop_mining(self) -> None:
        """Stop the current mining operation."""
        self.is_mining = False
        print("[PoW] Mining stopped")
    
    def is_mining_active(self) -> bool:
        """Check if mining is currently active."""
        return self.is_mining
    
    def get_mining_stats(self) -> Dict[str, Any]:
        """Get mining statistics."""
        return {
            'difficulty': self.difficulty,
            'target_block_time': self.target_block_time,
            'network_hash_rate': self.network_hash_rate,
            'total_blocks_mined': self.total_blocks_mined,
            'total_mining_time': self.total_mining_time,
            'is_mining': self.is_mining,
            'expected_block_time': self.calculate_expected_block_time(),
            'target_difficulty': self.calculate_target_difficulty(),
            'max_block_size': self.max_block_size,
            'confirmation_blocks': self.confirmation_blocks,
            'orphan_blocks_count': len(self.orphan_blocks),
            'chain_tips_count': len(self.chain_tips)
        }
    
    def get_performance_metrics(self, tx_per_block: int, tx_arrival_rate: float, power_draw: float) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        expected_block_time = self.calculate_expected_block_time()
        tps = self.calculate_transaction_throughput(tx_per_block, tx_arrival_rate)
        energy_per_block = self.calculate_energy_per_block(power_draw)
        
        return {
            'expected_block_time': expected_block_time,
            'transaction_throughput': tps,
            'energy_per_block': energy_per_block,
            'difficulty': self.difficulty,
            'network_hash_rate': self.network_hash_rate,
            'target_difficulty': self.calculate_target_difficulty(),
            'max_block_size': self.max_block_size,
            'confirmation_blocks': self.confirmation_blocks
        }
