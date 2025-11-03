"""
Block Header - Lightweight version of Block for efficient synchronization.

Block headers contain all information needed to verify the blockchain structure
without downloading full transaction data. This enables fast initial sync.
"""

from dataclasses import dataclass
from typing import Dict, Any
import hashlib
import json


@dataclass
class BlockHeader:
    """
    Lightweight block header for header-first synchronization.
    
    Contains only the essential information needed to verify chain integrity:
    - Block index and hash linkage
    - Proof of Work (hash, difficulty, nonce)
    - Timestamp for difficulty adjustment
    """
    block_index: int
    timestamp: float
    previous_hash: str
    hash: str
    miner: str
    difficulty: int
    nonce: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert header to dictionary for serialization."""
        return {
            'block_index': self.block_index,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'miner': self.miner,
            'difficulty': self.difficulty,
            'nonce': self.nonce
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlockHeader':
        """Create a BlockHeader instance from a dictionary."""
        return cls(
            block_index=data['block_index'],
            timestamp=data['timestamp'],
            previous_hash=data['previous_hash'],
            hash=data['hash'],
            miner=data.get('miner', data.get('validator', 'unknown')),
            difficulty=data.get('difficulty', 1),
            nonce=data.get('nonce', 0)
        )
    
    @classmethod
    def from_block(cls, block) -> 'BlockHeader':
        """
        Create a BlockHeader from a full Block.
        
        Extracts only the header information, discarding transactions and
        detailed energy metrics.
        """
        return cls(
            block_index=block.block_index,
            timestamp=block.timestamp,
            previous_hash=block.previous_hash,
            hash=block.hash,
            miner=block.miner,
            difficulty=block.energy_metrics.get('difficulty', 1),
            nonce=block.energy_metrics.get('nonce', 0)
        )
    
    def validate_pow(self) -> bool:
        """
        Validate the Proof of Work for this header.
        
        Verifies that the block hash meets the difficulty target.
        This is a critical security check - headers with invalid PoW
        indicate either corruption or a malicious peer.
        
        Returns:
            True if PoW is valid, False otherwise
        """
        # Calculate target difficulty using same formula as mining
        base_target = 2 ** 240  # Base target for difficulty 1
        target = base_target // self.difficulty
        
        # Constrain target to valid range
        min_target = 2 ** 224
        max_target = (2 ** 256) - 1
        target = max(min_target, min(max_target, target))
        
        # Convert hash to integer and check if it meets target
        hash_int = int(self.hash, 16)
        
        return hash_int < target
    
    def size_bytes(self) -> int:
        """
        Calculate approximate size of header in bytes.
        
        Used for bandwidth estimation during header sync.
        Headers are typically ~200 bytes vs full blocks at ~1-10KB.
        """
        return len(json.dumps(self.to_dict()).encode('utf-8'))


def validate_header_chain(headers: list['BlockHeader']) -> tuple[bool, str]:
    """
    Validate a chain of block headers.
    
    Performs comprehensive validation:
    1. Hash linkage - each header's previous_hash must match parent's hash
    2. Index continuity - indices must be sequential (0, 1, 2, 3, ...)
    3. Timestamp ordering - timestamps must increase monotonically
    4. Proof of Work - each header's hash must meet its difficulty target
    
    Args:
        headers: List of BlockHeader objects in order (genesis to tip)
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if chain is valid
        - (False, "error description") if invalid
    """
    if not headers:
        return False, "Empty header chain"
    
    # Validate genesis block
    if headers[0].block_index != 0:
        return False, f"First header must be genesis (index 0), got index {headers[0].block_index}"
    
    # Validate each header and its relationship to previous header
    for i in range(len(headers)):
        header = headers[i]
        
        # Validate PoW for this header
        if not header.validate_pow():
            return False, f"Invalid PoW at index {header.block_index} (hash: {header.hash[:16]}...)"
        
        # Validate relationship with previous header (skip genesis)
        if i > 0:
            prev_header = headers[i - 1]
            
            # Check index continuity
            if header.block_index != prev_header.block_index + 1:
                return False, f"Index discontinuity: {prev_header.block_index} → {header.block_index}"
            
            # Check hash linkage
            if header.previous_hash != prev_header.hash:
                return False, f"Hash linkage broken at index {header.block_index}: previous_hash doesn't match parent"
            
            # Check timestamp ordering (with small tolerance for clock skew)
            if header.timestamp < prev_header.timestamp - 1.0:  # 1 second tolerance
                return False, f"Timestamp ordering violated at index {header.block_index}"
    
    return True, ""


def calculate_header_chain_work(headers: list['BlockHeader']) -> int:
    """
    Calculate total proof-of-work for a header chain.
    
    Work is summed across all headers. Each header contributes
    work equal to its difficulty.
    
    Args:
        headers: List of BlockHeader objects
    
    Returns:
        Total cumulative work (sum of all difficulties)
    """
    return sum(header.difficulty for header in headers)

