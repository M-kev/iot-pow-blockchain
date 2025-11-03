from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import List, Dict, Any

@dataclass
class Block:
    block_index: int
    timestamp: float
    transactions: List[Dict[str, Any]]
    previous_hash: str
    miner: str  # Changed from validator to miner
    energy_metrics: Dict[str, float]
    
    def __post_init__(self):
        self.hash = self.calculate_hash()
        
    def calculate_hash(self) -> str:
        """Calculate the block hash using SHA-256."""
        # CRITICAL: Must EXACTLY match mining template structure
        # Use __original_metrics__ if available (from mining), otherwise reconstruct
        if '__original_metrics__' in self.energy_metrics:
            # This block was mined - use the original metrics that were hashed
            original_metrics = self.energy_metrics['__original_metrics__']
        else:
            # This block came from network - extract original metrics by removing added fields
            # Added fields during mining: mining_time, difficulty, nonce, hash_rate, energy_per_block, expected_block_time
            original_metrics = {k: v for k, v in self.energy_metrics.items() 
                               if k not in ['difficulty', 'nonce', 'mining_time', 'hash_rate', 
                                           'energy_per_block', 'expected_block_time', '__original_metrics__']}
        
        block_data = {
            'block_index': self.block_index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'miner': self.miner,
            'energy_metrics': original_metrics,  # ONLY original metrics (matches mining template)
            'difficulty': self.energy_metrics.get('difficulty', 1),
            'nonce': self.energy_metrics.get('nonce', 0)
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            'block_index': self.block_index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'miner': self.miner,
            'energy_metrics': self.energy_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create a Block instance from a dictionary."""
        return cls(
            block_index=data['block_index'],
            timestamp=data['timestamp'],
            transactions=data['transactions'],
            previous_hash=data['previous_hash'],
            miner=data.get('miner', data.get('validator', 'unknown')),  # Handle both old and new format
            energy_metrics=data['energy_metrics']
        )
    
    def get_pow_info(self) -> Dict[str, Any]:
        """Get PoW-specific information from the block."""
        return {
            'difficulty': self.energy_metrics.get('difficulty', 1),
            'nonce': self.energy_metrics.get('nonce', 0),
            'mining_time': self.energy_metrics.get('mining_time', 0),
            'hash_rate': self.energy_metrics.get('hash_rate', 0)
        } 