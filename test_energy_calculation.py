#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from consensus.pow import ProofOfWork
from consensus.block import Block
from storage.sqlite_storage import SQLiteStorage
from monitoring.metrics import BlockchainMetrics
import json
import time

def test_energy_calculation():
    """Test that energy calculation works correctly for mined blocks."""
    
    print("Testing PoW Energy Calculation...")
    
    # Initialize PoW consensus
    pow_consensus = ProofOfWork()
    
    # Create a test block data
    block_data = {
        'block_index': 1,
        'timestamp': time.time(),
        'transactions': [
            {
                'type': 'transfer',
                'sender': 'pi_node_2',
                'recipient': 'pi_node_1',
                'amount': 10.0,
                'timestamp': time.time()
            }
        ],
        'previous_hash': '0' * 64,  # Genesis block hash
        'miner': 'pi_node_2',
        'energy_metrics': {
            'cpu_percent': 50.0,
            'memory_percent': 30.0,
            'temperature': 45.0,
            'power_usage': 2.5  # 2.5W power draw
        }
    }
    
    print(f"Block data: {json.dumps(block_data, indent=2)}")
    
    # Mine a block
    print("\nMining block...")
    mined_block = pow_consensus.mine_block(block_data, max_time=10.0)
    
    if mined_block:
        print(f"Block mined successfully!")
        print(f"Block index: {mined_block.block_index}")
        print(f"Miner: {mined_block.miner}")
        print(f"Energy metrics: {json.dumps(mined_block.energy_metrics, indent=2)}")
        
        # Check if energy_per_block is calculated
        if 'energy_per_block' in mined_block.energy_metrics:
            energy_per_block = mined_block.energy_metrics['energy_per_block']
            power_usage = mined_block.energy_metrics['power_usage']
            mining_time = mined_block.energy_metrics['mining_time']
            
            print(f"\nEnergy calculation:")
            print(f"  Power usage: {power_usage}W")
            print(f"  Mining time: {mining_time:.2f}s")
            print(f"  Energy per block: {energy_per_block:.2f}W")
            print(f"  Expected: {power_usage * mining_time:.2f}W")
            
            # Verify calculation
            expected_energy = power_usage * mining_time
            if abs(energy_per_block - expected_energy) < 0.01:
                print("✅ Energy calculation is correct!")
            else:
                print("❌ Energy calculation is incorrect!")
        else:
            print("❌ energy_per_block not found in block energy metrics!")
    else:
        print("❌ Failed to mine block!")
    
    # Test cumulative energy calculation
    print("\nTesting cumulative energy calculation...")
    
    # Create storage and metrics
    storage = SQLiteStorage('test_energy.db')
    metrics = BlockchainMetrics('test_node', storage)
    
    # Save the mined block
    if mined_block:
        storage.save_block(mined_block)
        
        # Calculate cumulative energy
        cumulative_energy = metrics.get_cumulative_mining_power()
        print(f"Cumulative mining energy: {cumulative_energy:.2f}W")
        
        if cumulative_energy > 0:
            print("✅ Cumulative energy calculation is working!")
        else:
            print("❌ Cumulative energy calculation returned 0!")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_energy_calculation()
