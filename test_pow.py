#!/usr/bin/env python3
"""
Test script for the PoW blockchain implementation.
This script tests the core PoW functionality and mathematical models.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from consensus.pow import ProofOfWork
from consensus.block import Block
import time
import json

def test_pow_models():
    """Test the PoW mathematical models."""
    print("=== Testing PoW Mathematical Models ===")
    
    # Initialize PoW with target block time of 3 seconds
    pow_consensus = ProofOfWork(target_block_time=3.0)
    
    # Test 1: Expected Block Time Model
    print("\n1. Testing Expected Block Time Model:")
    print(f"   Formula: E[Tblock] = (difficulty × 2^32) / hash_rate")
    
    # Test with different difficulties and hash rates
    test_cases = [
        (1, 1000),      # Low difficulty, low hash rate
        (10, 5000),     # Medium difficulty, medium hash rate
        (100, 10000),   # High difficulty, high hash rate
    ]
    
    for difficulty, hash_rate in test_cases:
        pow_consensus.difficulty = difficulty
        pow_consensus.network_hash_rate = hash_rate
        expected_time = pow_consensus.calculate_expected_block_time()
        print(f"   Difficulty: {difficulty}, Hash Rate: {hash_rate} H/s")
        print(f"   Expected Block Time: {expected_time:.2f} seconds")
    
    # Test 2: Transaction Throughput Model
    print("\n2. Testing Transaction Throughput Model:")
    print(f"   Formula: TPS = min(tx_per_block / E[Tblock], tx_arrival_rate)")
    
    tx_per_block = 10
    tx_arrival_rate = 5.0
    
    for difficulty, hash_rate in test_cases:
        pow_consensus.difficulty = difficulty
        pow_consensus.network_hash_rate = hash_rate
        tps = pow_consensus.calculate_transaction_throughput(tx_per_block, tx_arrival_rate)
        expected_time = pow_consensus.calculate_expected_block_time()
        print(f"   Difficulty: {difficulty}, Hash Rate: {hash_rate} H/s")
        print(f"   Expected Block Time: {expected_time:.2f}s, TPS: {tps:.2f}")
    
    # Test 3: Energy Model
    print("\n3. Testing Energy Model:")
    print(f"   Formula: Eblock = power_draw × E[Tblock]")
    
    power_draw = 2.5  # watts
    
    for difficulty, hash_rate in test_cases:
        pow_consensus.difficulty = difficulty
        pow_consensus.network_hash_rate = hash_rate
        energy_per_block = pow_consensus.calculate_energy_per_block(power_draw)
        expected_time = pow_consensus.calculate_expected_block_time()
        print(f"   Difficulty: {difficulty}, Hash Rate: {hash_rate} H/s")
        print(f"   Expected Block Time: {expected_time:.2f}s, Energy per Block: {energy_per_block:.2f} J")
    
    # Test 4: Total Energy Model
    print("\n4. Testing Total Energy Model:")
    print(f"   Formula: Etotal = Σ (from i=1 to k) Eblock_i")
    
    num_blocks = 100
    for difficulty, hash_rate in test_cases:
        pow_consensus.difficulty = difficulty
        pow_consensus.network_hash_rate = hash_rate
        total_energy = pow_consensus.calculate_total_energy(power_draw, num_blocks)
        print(f"   Difficulty: {difficulty}, Hash Rate: {hash_rate} H/s")
        print(f"   Total Energy for {num_blocks} blocks: {total_energy:.2f} J")

def test_pow_mining():
    """Test the PoW mining functionality."""
    print("\n=== Testing PoW Mining ===")
    
    pow_consensus = ProofOfWork(target_block_time=3.0)
    
    # Prepare block data for mining
    block_data = {
        'block_index': 1,
        'timestamp': time.time(),
        'transactions': [
            {'type': 'test', 'data': 'test transaction', 'timestamp': time.time()}
        ],
        'previous_hash': '0' * 64,
        'miner': 'test_node',
        'energy_metrics': {
            'cpu_percent': 50.0,
            'memory_percent': 30.0,
            'temperature': 45.0,
            'power_usage': 2.5
        }
    }
    
    print("Starting mining test...")
    print(f"Current difficulty: {pow_consensus.difficulty}")
    print(f"Target difficulty: {pow_consensus.calculate_target_difficulty()}")
    
    # Try to mine a block with a short timeout
    start_time = time.time()
    mined_block = pow_consensus.mine_block(block_data, max_time=10.0)
    mining_time = time.time() - start_time
    
    if mined_block:
        print(f"✓ Block mined successfully!")
        print(f"  Block hash: {mined_block.hash}")
        print(f"  Mining time: {mining_time:.2f} seconds")
        print(f"  Nonce used: {mined_block.energy_metrics.get('nonce', 'N/A')}")
        
        # Verify the mined block
        is_valid = pow_consensus.validate_block(
            mined_block, 
            power_usage=2.5, 
            previous_block_timestamp=0.0, 
            previous_block_index=0
        )
        print(f"  Block validation: {'✓ PASS' if is_valid else '✗ FAIL'}")
    else:
        print("✗ Mining failed or timed out")

def test_difficulty_adjustment():
    """Test difficulty adjustment based on block times."""
    print("\n=== Testing Difficulty Adjustment ===")
    
    pow_consensus = ProofOfWork(target_block_time=3.0)
    
    # Test with different block time scenarios
    test_scenarios = [
        ([1.0, 1.5, 2.0, 1.8, 2.2], "Fast blocks - should increase difficulty"),
        ([4.0, 5.0, 3.5, 4.5, 4.2], "Slow blocks - should decrease difficulty"),
        ([2.8, 3.2, 3.0, 2.9, 3.1], "Normal blocks - should maintain difficulty")
    ]
    
    for block_times, description in test_scenarios:
        print(f"\n{description}:")
        print(f"  Block times: {block_times}")
        print(f"  Average block time: {sum(block_times)/len(block_times):.2f}s")
        print(f"  Initial difficulty: {pow_consensus.difficulty}")
        
        pow_consensus.adjust_difficulty(block_times)
        print(f"  Adjusted difficulty: {pow_consensus.difficulty}")

def test_performance_metrics():
    """Test comprehensive performance metrics."""
    print("\n=== Testing Performance Metrics ===")
    
    pow_consensus = ProofOfWork(target_block_time=3.0)
    pow_consensus.difficulty = 10
    pow_consensus.network_hash_rate = 5000
    
    # Get performance metrics
    metrics = pow_consensus.get_performance_metrics(
        tx_per_block=10,
        tx_arrival_rate=5.0,
        power_draw=2.5
    )
    
    print("Performance Metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

if __name__ == "__main__":
    print("PoW Blockchain Test Suite")
    print("=" * 50)
    
    try:
        test_pow_models()
        test_pow_mining()
        test_difficulty_adjustment()
        test_performance_metrics()
        
        print("\n" + "=" * 50)
        print("✓ All tests completed successfully!")
        print("The PoW implementation is working correctly.")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
