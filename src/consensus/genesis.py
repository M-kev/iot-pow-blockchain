import json
import os
from typing import Dict, Any
from .block import Block

class GenesisBlock:
    def __init__(self):
        # PoW doesn't need initial stakes, but we can track initial network participants
        self.initial_network_participants = [
            "pi_node_1",
            "pi_node_2", 
            "pi_node_3",
            "pi_node_4",
            "pi_node_5",
            "pi_node_6"
        ]
        self.fixed_timestamp = 1717777777  # Use a constant value for determinism
        self.initial_difficulty = 1  # Initial mining difficulty for PoW
        
    def create_genesis_block(self) -> Block:
        """Create the genesis block with initial network configuration."""
        genesis_data = {
            "timestamp": self.fixed_timestamp,
            "transactions": [
                {
                    "type": "network_init",
                    "data": {
                        "participants": self.initial_network_participants,
                        "initial_difficulty": self.initial_difficulty,
                        "consensus_type": "proof_of_work"
                    },
                    "timestamp": self.fixed_timestamp
                }
            ],
            "energy_metrics": {
                "cpu_percent": 0,
                "memory_percent": 0,
                "temperature": 0,
                "power_usage": 0,
                "difficulty": self.initial_difficulty,
                "nonce": 0,
                "mining_time": 0,
                "hash_rate": 1000  # Initial hash rate estimate
            }
        }
        
        # Create genesis block
        genesis_block = Block(
            block_index=0,
            timestamp=genesis_data["timestamp"],
            transactions=genesis_data["transactions"],
            previous_hash="0" * 64,  # First block has no previous hash
            miner="genesis",
            energy_metrics=genesis_data["energy_metrics"]
        )
        
        return genesis_block
        
    def get_initial_network_config(self) -> Dict[str, Any]:
        """Get the initial network configuration."""
        return {
            "participants": self.initial_network_participants,
            "initial_difficulty": self.initial_difficulty,
            "consensus_type": "proof_of_work"
        }
        
    def save_genesis_block(self, filepath: str = "blockchain_data/genesis.json") -> None:
        """Save genesis block to file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        genesis_block = self.create_genesis_block()
        genesis_data = genesis_block.to_dict()
        
        with open(filepath, 'w') as f:
            json.dump(genesis_data, f, indent=2)
        
        print(f"Genesis block saved to {filepath}")
    
    def load_genesis_block(self, filepath: str = "blockchain_data/genesis.json") -> Block:
        """Load genesis block from file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Genesis block file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            genesis_data = json.load(f)
        
        return Block.from_dict(genesis_data)
    
    def verify_genesis_block(self, block: Block) -> bool:
        """Verify that a block is a valid genesis block."""
        genesis_block = self.create_genesis_block()
        
        return (
            block.block_index == genesis_block.block_index and
            block.previous_hash == genesis_block.previous_hash and
            block.miner == genesis_block.miner and
            block.transactions[0]['type'] == genesis_block.transactions[0]['type'] and
            block.transactions[0]['data']['consensus_type'] == genesis_block.transactions[0]['data']['consensus_type']
        ) 