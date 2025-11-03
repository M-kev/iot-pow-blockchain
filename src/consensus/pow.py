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
        self.difficulty = 1  # Start with difficulty 1 (correct for testing)
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
        self.network_hash_rate = 1000000  # Initial hash rate 1 MH/s (more realistic)
        self.last_difficulty_adjustment = time.time()
        self.difficulty_adjustment_interval = 10  # Adjust difficulty every 10 blocks (more frequent for testing)
        
        # Block time tracking for difficulty adjustment
        self.recent_block_times = []
        self.max_block_times_history = 2016
        
        # Mining statistics
        self.total_blocks_mined = 0
        self.total_mining_time = 0
        self.total_energy_consumed = 0
        self.last_mining_time = None  # Track when we last mined
        
        # Bitcoin-style consensus rules
        self.max_block_size = 1024 * 1024  # 1MB block size limit (like Bitcoin)
        self.confirmation_blocks = 6  # Number of confirmations for finality (like Bitcoin)
        self.orphan_blocks: Dict[str, Dict[str, Any]] = {}  # Store orphaned blocks with metadata {'block': Block, 'timestamp': float, 'block_index': int}
        self.pending_blocks: Dict[str, Block] = {}  # Store blocks waiting for parent
        self.chain_tips: Dict[str, Block] = {}  # Multiple chain tips for fork resolution
        
    def calculate_target_difficulty(self) -> int:
        """Calculate the target difficulty based on current network conditions."""
        # For testing purposes, we want a reasonable target that requires some work
        # but isn't impossible to achieve
        
        if self.difficulty <= 0:
            return 2**256 - 1  # Maximum target (easiest)
        
        # For difficulty 1, we want to require some work but not too much
        # Let's say we want approximately 1 in 2^16 hashes to be valid for difficulty 1
        # This means target = 2^256 / 2^16 = 2^240
        
        # Scale this with difficulty: target = 2^240 / difficulty
        base_target = 2**240  # Base target for difficulty 1
        target = base_target // self.difficulty
        
        # Ensure target is within reasonable bounds
        min_target = 2**224  # Minimum target (hardest)
        max_target = 2**256 - 1  # Maximum target (easiest)
        
        target = max(min_target, min(max_target, target))
        
        return target
    
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
        When work is equal, prefer longer chain, then use deterministic hash tie-breaker.
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
            elif chain_work == best_work and chain_work > 0:
                # Tie-breaker: when work is equal, prefer longer chain
                if len(chain) > len(best_chain):
                    best_chain = chain
                elif len(chain) == len(best_chain) and len(chain) > 0:
                    # If length is also equal, use deterministic tie-breaker: lowest hash of tip block
                    # This ensures all nodes make the same choice
                    chain_tip_hash = chain[-1].hash
                    best_tip_hash = best_chain[-1].hash
                    if chain_tip_hash < best_tip_hash:
                        best_chain = chain
        
        return best_chain
    
    def _build_all_chains(self, blocks: List[Block]) -> List[List[Block]]:
        """Build all possible chains from the given blocks. Only includes complete chains from genesis."""
        if not blocks:
            return []
        
        # Create a map of block hash to block
        block_map = {block.hash: block for block in blocks}
        
        # Find genesis block(s) - blocks with previous_hash = "0"*64 or block_index = 0
        genesis_blocks = [b for b in blocks if b.block_index == 0 or b.previous_hash == "0" * 64]
        
        # If no genesis found, return empty (invalid state)
        if not genesis_blocks:
            print("[PoW] WARNING: No genesis block found in blocks!")
            return []
        
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
            visited = set()  # Prevent cycles
            
            while current_hash in block_map and current_hash not in visited:
                visited.add(current_hash)
                block = block_map[current_hash]
                chain.append(block)
                
                # Stop if we reached genesis
                if block.block_index == 0 or block.previous_hash == "0" * 64:
                    break
                    
                current_hash = block.previous_hash
            
            # Only include chains that start from genesis (block_index 0)
            if chain and chain[-1].block_index == 0:
                # Reverse to get genesis to tip order
                chain.reverse()
                chains.append(chain)
            elif chain:
                # Chain doesn't connect to genesis - might be incomplete
                print(f"[PoW] WARNING: Chain ending at {chain[0].hash[:16]}... doesn't connect to genesis")
        
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
    
    def handle_orphan_block(self, block: Block, all_blocks: List[Block] = None) -> bool:
        """
        Handle orphan blocks (blocks whose parent we don't have yet).
        Returns True if the block was added to pending blocks.
        
        Args:
            block: The block to check for orphan status
            all_blocks: Optional list of all blocks to check against (if None, uses chain_tips)
        """
        # Check if we have the parent block - check against provided blocks or all chain tips
        if all_blocks:
            parent_exists = any(b.hash == block.previous_hash for b in all_blocks)
        else:
            parent_exists = any(b.hash == block.previous_hash for b in self.chain_tips.values())
        
        if not parent_exists:
            # Store as orphan block with timestamp for cleanup
            self.orphan_blocks[block.hash] = {
                'block': block,
                'timestamp': time.time(),
                'block_index': block.block_index
            }
            print(f"[PoW] Stored orphan block {block.hash[:16]}... (index {block.block_index}, parent {block.previous_hash[:16]}... not found)")
            return True
        
        return False
    
    def cleanup_old_orphans(self, max_age_seconds: float = 60.0) -> int:
        """
        Remove orphan blocks that are too old and can't be connected.
        Returns number of orphan blocks cleaned up.
        """
        current_time = time.time()
        cleaned = 0
        
        orphan_hashes = list(self.orphan_blocks.keys())
        for orphan_hash in orphan_hashes:
            orphan_entry = self.orphan_blocks[orphan_hash]
            age = current_time - orphan_entry['timestamp']
            
            # Remove orphan blocks older than max_age_seconds
            if age > max_age_seconds:
                print(f"[PoW] Cleaning up old orphan block {orphan_hash[:16]}... (index {orphan_entry['block_index']}, age {age:.1f}s)")
                del self.orphan_blocks[orphan_hash]
                cleaned += 1
        
        return cleaned
    
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
            orphan_entry = self.orphan_blocks[orphan_hash]
            orphan_block = orphan_entry['block']
            
            # Check if parent is now in main chain
            parent_in_chain = any(b.hash == orphan_block.previous_hash for b in updated_chain)
            
            if parent_in_chain:
                # Validate the orphan block
                previous_block = next((b for b in updated_chain if b.hash == orphan_block.previous_hash), None)
                if previous_block:
                    prev_timestamp = previous_block.timestamp
                    prev_index = previous_block.block_index
                else:
                    prev_timestamp = 0.0
                    prev_index = -1
                
                # Validate orphan block now that parent is available
                # Get all blocks for parent lookup (main chain + orphan block being processed)
                all_blocks_for_validation = updated_chain + [orphan_block]
                if self.validate_block(orphan_block, 0.0, prev_timestamp, prev_index, all_stored_blocks=all_blocks_for_validation):
                    # Add to chain in correct position (after parent)
                    parent_idx = next((i for i, b in enumerate(updated_chain) if b.hash == orphan_block.previous_hash), len(updated_chain))
                    updated_chain.insert(parent_idx + 1, orphan_block)
                    processed_blocks.append(orphan_block)
                    print(f"[PoW] Added orphan block {orphan_hash[:16]}... (index {orphan_block.block_index}) to chain")
                
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
        
        # Debug: Show all chains found
        chains = self._build_all_chains(all_blocks)
        if len(chains) > 1:
            print(f"[PoW] Fork resolution: Found {len(chains)} competing chains:")
            for i, chain in enumerate(chains):
                chain_indices = [b.block_index for b in chain]
                chain_work = self.calculate_chain_work(chain)
                chain_tip = chain[-1].hash[:16] if chain else "none"
                is_best = (chain == best_chain)
                marker = " <-- BEST" if is_best else ""
                print(f"  Chain {i+1}: indices {chain_indices}, work={chain_work}, tip={chain_tip}...{marker}")
        
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
        print(f"[PoW] Target in hex: {hex(target_difficulty)}")
        print(f"[PoW] Max nonce: {self.max_nonce}")
        
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
                print(f"[PoW] Valid hash found at nonce {nonce}!")
                print(f"[PoW] Hash: {block_hash}")
                print(f"[PoW] Hash int: {hash_int}")
                print(f"[PoW] Target: {target_difficulty}")
                print(f"[PoW] Hash < Target: {hash_int < target_difficulty}")
                mining_time = time.time() - start_time
                self.is_mining = False
                
                # Calculate power usage during mining
                # Use the actual mining time: Eblock = power_draw × actual_mining_time
                power_draw = block_template['energy_metrics'].get('power_usage', 1.0)  # Default 1W
                energy_per_block = power_draw * mining_time  # Use actual mining time, not expected time
                
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
                        'expected_block_time': self.calculate_expected_block_time()
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
                self.last_mining_time = time.time()  # Track when we last mined
                
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
    
    def validate_block(self, block: Block, power_usage: float, previous_block_timestamp: float, previous_block_index: int, sync_tolerance: float = 0.0, all_stored_blocks: List[Block] = None) -> bool:
        """
        Validate a block based on PoW rules and energy efficiency.
        
        Args:
            block: Block to validate
            power_usage: Current power usage
            previous_block_timestamp: Timestamp of previous block (from block's parent)
            previous_block_index: Index of previous block (from block's parent)
            sync_tolerance: Time tolerance for synchronization
            all_stored_blocks: All blocks in storage (for checking if parent exists in any fork)
            
        Returns:
            True if block is valid, False otherwise
        """
        print(f"[PoW VALIDATE] Validating block {block.block_index}")
        
        # Find the actual parent block in storage (may be in a different fork)
        parent_block = None
        if all_stored_blocks:
            for stored_block in all_stored_blocks:
                if stored_block.hash == block.previous_hash:
                    parent_block = stored_block
                    break
        
        # If parent exists, validate against parent's index/timestamp
        # If parent doesn't exist (except for genesis), block is orphaned
        if block.block_index == 0:
            # Genesis block - special validation
            pass
        elif block.previous_hash == "0" * 64:
            # Genesis parent hash - invalid for non-genesis blocks
            print(f"[PoW VALIDATE] Non-genesis block has genesis parent hash")
            return False
        elif parent_block:
            # Parent found - validate against parent
            if block.block_index != parent_block.block_index + 1:
                print(f"[PoW VALIDATE] Block index {block.block_index} should be {parent_block.block_index + 1} (parent index + 1)")
                return False
            if block.timestamp <= parent_block.timestamp - sync_tolerance:
                print(f"[PoW VALIDATE] Block timestamp {block.timestamp} is not greater than parent {parent_block.timestamp}")
                return False
        else:
            # Parent not found - this is an orphan block (will be stored for later)
            # Don't validate index/timestamp constraints since we don't know the parent
            print(f"[PoW VALIDATE] Parent block not found - treating as orphan (will validate when parent arrives)")
            # Still validate other constraints (size, PoW) - orphan blocks are stored and validated later
        
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
        # CRITICAL: Must match mining template structure exactly
        # difficulty/nonce are at top level, NOT in energy_metrics during mining
        # So we extract them from energy_metrics and put them at top level
        block_data = {
            'block_index': block.block_index,
            'timestamp': block.timestamp,
            'transactions': block.transactions,
            'previous_hash': block.previous_hash,
            'miner': block.miner,
            # energy_metrics WITHOUT difficulty/nonce (matches mining template)
            'energy_metrics': {k: v for k, v in block.energy_metrics.items() if k not in ['difficulty', 'nonce']},
            # difficulty/nonce at top level (matches mining template)
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
        
        # CRITICAL: Verify hash meets target difficulty using the BLOCK'S difficulty, not receiver's
        # Each block is mined with a specific difficulty, and that's what we validate against
        block_difficulty = block.energy_metrics.get('difficulty', 1)
        
        # Calculate target using the block's difficulty
        # Target = (2^240) / difficulty, constrained between 2^224 and 2^256-1
        base_target = 2 ** 240  # Base target for difficulty 1
        target_for_block = base_target // block_difficulty
        
        # Constrain target
        min_target = 2 ** 224
        max_target = (2 ** 256) - 1
        target_for_block = max(min_target, min(max_target, target_for_block))
        
        hash_int = int(calculated_hash, 16)
        
        if hash_int >= target_for_block:
            print(f"[PoW VALIDATE] Hash {calculated_hash} does not meet target difficulty")
            print(f"  Block difficulty: {block_difficulty}, Target: {target_for_block}, Hash int: {hash_int}")
            return False
        
        return True
    
    def adjust_difficulty(self, recent_block_times: List[float]) -> None:
        """
        Adjust mining difficulty based on recent block times.
        
        Args:
            recent_block_times: List of recent block intervals
        """
        if len(recent_block_times) < 5:  # Need at least 5 blocks for adjustment (more responsive)
            return
        
        # Calculate average block time
        avg_block_time = sum(recent_block_times) / len(recent_block_times)
        
        # More aggressive difficulty adjustment based on how far off we are
        time_ratio = avg_block_time / self.target_block_time
        
        if time_ratio > 1.5:  # Much too slow (>50% slower)
            adjustment_factor = 0.7  # Reduce difficulty by 30%
            self.difficulty = max(self.min_difficulty, int(self.difficulty * adjustment_factor))
            print(f"[PoW] Significantly decreasing difficulty to {self.difficulty} (avg block time: {avg_block_time:.2f}s, ratio: {time_ratio:.2f})")
        elif time_ratio > 1.1:  # Too slow (>10% slower)
            adjustment_factor = 0.85  # Reduce difficulty by 15%
            self.difficulty = max(self.min_difficulty, int(self.difficulty * adjustment_factor))
            print(f"[PoW] Decreasing difficulty to {self.difficulty} (avg block time: {avg_block_time:.2f}s, ratio: {time_ratio:.2f})")
        elif time_ratio < 0.5:  # Much too fast (<50% of target)
            adjustment_factor = 2.0  # Double difficulty
            self.difficulty = min(self.max_difficulty, int(self.difficulty * adjustment_factor))
            print(f"[PoW] Significantly increasing difficulty to {self.difficulty} (avg block time: {avg_block_time:.2f}s, ratio: {time_ratio:.2f})")
        elif time_ratio < 0.9:  # Too fast (<90% of target)
            adjustment_factor = 1.3  # Increase difficulty by 30%
            self.difficulty = min(self.max_difficulty, int(self.difficulty * adjustment_factor))
            print(f"[PoW] Increasing difficulty to {self.difficulty} (avg block time: {avg_block_time:.2f}s, ratio: {time_ratio:.2f})")
        else:
            print(f"[PoW] Difficulty unchanged at {self.difficulty} (avg block time: {avg_block_time:.2f}s, ratio: {time_ratio:.2f})")
    
    def update_network_hash_rate(self, new_hash_rate: float) -> None:
        """Update the network hash rate estimate."""
        self.network_hash_rate = new_hash_rate
        print(f"[PoW] Updated network hash rate to {new_hash_rate} H/s")
    
    def calculate_expected_block_time(self) -> float:
        """
        Calculate expected block time using the correct PoW model: E[Tblock] = (difficulty × 2^32) / hash_rate
        This is the standard Bitcoin formula.
        """
        if self.network_hash_rate <= 0:
            return float('inf')
        
        # Correct PoW formula: E[Tblock] = (difficulty × 2^32) / hash_rate
        expected_time = (self.difficulty * 2**32) / self.network_hash_rate
        
        # For testing, cap at reasonable bounds (between 0.1 and 300 seconds)
        expected_time = max(0.1, min(300.0, expected_time))
        
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
        This is used for estimates, actual energy is calculated from real mining time.
        """
        expected_block_time = self.calculate_expected_block_time()
        energy_per_block = power_draw * expected_block_time
        
        # Ensure reasonable bounds (between 0.1 and 1000 watt-seconds)
        energy_per_block = max(0.1, min(1000.0, energy_per_block))
        
        return energy_per_block
    
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
        # Consider mining active if we've mined blocks recently or are currently mining
        # This provides a more meaningful status for the dashboard
        current_time = time.time()
        recent_mining_threshold = 30  # Consider "active" if we mined in the last 30 seconds
        
        # Check if we're currently mining
        if self.is_mining:
            return True
        
        # Check if we've mined recently (within the threshold)
        if hasattr(self, 'last_mining_time') and self.last_mining_time:
            time_since_last_mining = current_time - self.last_mining_time
            if time_since_last_mining < recent_mining_threshold:
                return True
        
        return False
    
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
