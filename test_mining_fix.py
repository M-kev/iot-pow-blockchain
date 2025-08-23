#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from consensus.pow import ProofOfWork
import time

def test_mining_fix():
    """Test that the mining method works with the fixed signature."""
    
    print("Testing PoW Mining Fix...")
    
    # Initialize PoW consensus
    pow_consensus = ProofOfWork()
    
    # Test the energy calculation method
    power_draw = 2.5
    energy_per_block = pow_consensus.calculate_energy_per_block(power_draw)
    print(f"✅ Energy per block calculation works: {energy_per_block:.2f}W")
    
    # Test mining a simple block
    block_data = {
        'block_index': 1,
        'timestamp': time.time(),
        'transactions': [],
        'previous_hash': '0' * 64,
        'miner': 'test_node',
        'energy_metrics': {
            'cpu_percent': 50.0,
            'memory_percent': 30.0,
            'temperature': 45.0,
            'power_usage': power_draw
        }
    }
    
    print("Mining test block...")
    mined_block = pow_consensus.mine_block(block_data, max_time=5.0)
    
    if mined_block:
        print(f"✅ Mining successful!")
        print(f"Block hash: {mined_block.hash}")
        print(f"Energy metrics: {mined_block.energy_metrics}")
        
        # Check that energy_per_block is calculated
        if 'energy_per_block' in mined_block.energy_metrics:
            print(f"✅ Energy per block: {mined_block.energy_metrics['energy_per_block']:.2f}W")
        else:
            print("❌ Energy per block not found in block")
    else:
        print("❌ Mining failed")
    
    print("Test completed!")

if __name__ == "__main__":
    test_mining_fix()
