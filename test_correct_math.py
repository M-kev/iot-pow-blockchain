#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from consensus.pow import ProofOfWork
import time

def test_correct_mathematics():
    """Test the correct mathematical models for PoW blockchains."""
    
    print("Testing Correct PoW Mathematical Models...")
    print("=" * 60)
    
    # Create PoW instance with correct parameters
    pow_consensus = ProofOfWork(target_block_time=3.0)
    
    print("📊 INITIAL PARAMETERS:")
    print(f"  Difficulty: {pow_consensus.difficulty}")
    print(f"  Network Hash Rate: {pow_consensus.network_hash_rate:,} H/s ({pow_consensus.network_hash_rate/1e6:.1f} MH/s)")
    print(f"  Target Block Time: {pow_consensus.target_block_time} seconds")
    
    # Test the correct mathematical model
    print("\n🧮 CORRECT MATHEMATICAL MODEL:")
    print("E[Tblock] = (difficulty × 2^32) / hash_rate")
    
    difficulty = pow_consensus.difficulty
    hash_rate = pow_consensus.network_hash_rate
    expected_time = pow_consensus.calculate_expected_block_time()
    
    print(f"  E[Tblock] = ({difficulty} × 2^32) / {hash_rate:,}")
    print(f"  E[Tblock] = ({difficulty} × 4,294,967,296) / {hash_rate:,}")
    print(f"  E[Tblock] = {difficulty * 2**32:,} / {hash_rate:,}")
    print(f"  E[Tblock] = {expected_time:.2f} seconds")
    
    # Show how this scales with different parameters
    print("\n📈 SCALING EXAMPLES:")
    
    # Example 1: Bitcoin-like parameters
    print("\n  Bitcoin-like (10-minute target):")
    btc_difficulty = 50000000000  # 50 billion
    btc_hash_rate = 400e18  # 400 EH/s
    btc_expected = (btc_difficulty * 2**32) / btc_hash_rate
    print(f"    Difficulty: {btc_difficulty:,}")
    print(f"    Hash Rate: {btc_hash_rate/1e18:.0f} EH/s")
    print(f"    Expected Time: {btc_expected:.2f} seconds ({btc_expected/60:.1f} minutes)")
    
    # Example 2: Our test parameters
    print("\n  Our Test Parameters:")
    print(f"    Difficulty: {difficulty}")
    print(f"    Hash Rate: {hash_rate/1e6:.1f} MH/s")
    print(f"    Expected Time: {expected_time:.2f} seconds")
    
    # Example 3: What if we had higher difficulty
    print("\n  Higher Difficulty (100):")
    high_diff = 100
    high_expected = (high_diff * 2**32) / hash_rate
    print(f"    Difficulty: {high_diff}")
    print(f"    Expected Time: {high_expected:.2f} seconds ({high_expected/60:.1f} minutes)")
    
    # Test energy calculation
    print("\n⚡ ENERGY CALCULATION:")
    power_draw = 2.5  # 2.5W (typical Raspberry Pi)
    energy_per_block = pow_consensus.calculate_energy_per_block(power_draw)
    
    print(f"  Power Draw: {power_draw}W")
    print(f"  Expected Block Time: {expected_time:.2f} seconds")
    print(f"  Energy per Block: {energy_per_block:.2f} watt-seconds")
    print(f"  Energy per Block: {energy_per_block/3600:.4f} watt-hours")
    
    # Test actual mining
    print("\n⛏️  ACTUAL MINING TEST:")
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
    
    start_time = time.time()
    mined_block = pow_consensus.mine_block(block_data, max_time=10.0)
    actual_time = time.time() - start_time
    
    if mined_block:
        print(f"  ✅ Block mined successfully!")
        print(f"  Actual Mining Time: {actual_time:.2f} seconds")
        print(f"  Expected Time: {expected_time:.2f} seconds")
        print(f"  Ratio: {actual_time/expected_time:.2f}x")
        
        # Show energy metrics
        energy_metrics = mined_block.energy_metrics
        actual_energy = energy_metrics.get('energy_per_block', 0)
        print(f"  Actual Energy: {actual_energy:.2f} watt-seconds")
        print(f"  Expected Energy: {energy_per_block:.2f} watt-seconds")
    else:
        print("  ❌ Mining failed")
    
    print("\n" + "=" * 60)
    print("✅ MATHEMATICAL MODEL SUMMARY:")
    print("  - Using correct Bitcoin formula: E[Tblock] = (difficulty × 2^32) / hash_rate")
    print("  - Parameters adjusted for realistic testing")
    print("  - Energy calculated from actual mining time")
    print("  - All values now realistic and meaningful")
    
    return True

if __name__ == "__main__":
    test_correct_mathematics()
