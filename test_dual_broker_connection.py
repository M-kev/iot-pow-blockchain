#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from network.mqtt_client import MQTTClient
from config.network_config import get_node_config, MQTT_BROKERS
import time
import json

def test_dual_broker_connection():
    """Test that nodes connect to both MQTT brokers."""
    
    print("Testing Dual MQTT Broker Connection...")
    print("=" * 50)
    
    # Show broker configuration
    print("MQTT Broker Configuration:")
    for i, broker in enumerate(MQTT_BROKERS):
        print(f"  Broker {i + 1}: {broker['host']}:{broker['port']}")
    
    # Test with Node 1 configuration
    node_id = "pi_node_1"
    node_config = get_node_config(node_id)
    
    if not node_config:
        print(f"❌ Node config not found for {node_id}")
        return
    
    print(f"\nTesting with {node_id} config: {node_config}")
    
    # Create MQTT client
    mqtt_client = MQTTClient(node_id, node_config)
    
    # Try to connect to both brokers
    print("\nAttempting to connect to both MQTT brokers...")
    connection_result = mqtt_client.connect()
    
    if not connection_result:
        print("❌ Failed to connect to any MQTT broker")
        return
    
    print("✅ Connected to MQTT broker(s)")
    
    # Wait a moment for connections to stabilize
    time.sleep(3)
    
    # Get network status
    network_status = mqtt_client.get_network_status()
    print(f"\nNetwork Status: {json.dumps(network_status, indent=2)}")
    
    # Check which brokers are active
    active_brokers = network_status.get('active_brokers', [])
    print(f"\nActive Brokers: {len(active_brokers)}")
    for broker in active_brokers:
        print(f"  ✅ {broker}")
    
    # Test publishing metrics to both brokers
    print("\nTesting metrics publishing to both brokers...")
    test_metrics = {
        'node_id': node_id,
        'timestamp': time.time(),
        'cpu_percent': 45.2,
        'memory_percent': 32.1,
        'temperature': 48.5,
        'power_usage': 1.8,
        'block_count': 5,
        'pending_transactions': 2,
        'hash_rate': 1000,
        'difficulty': 1,
        'is_mining': True
    }
    
    print(f"Publishing metrics: {json.dumps(test_metrics, indent=2)}")
    mqtt_client.publish_metrics(test_metrics)
    
    # Wait a moment for publishing
    time.sleep(2)
    
    # Test publishing a block to both brokers
    print("\nTesting block publishing to both brokers...")
    test_block = {
        'block_index': 1,
        'timestamp': time.time(),
        'transactions': [],
        'previous_hash': '0' * 64,
        'miner': node_id,
        'hash': 'test_hash_123',
        'energy_metrics': {
            'cpu_percent': 50.0,
            'memory_percent': 30.0,
            'temperature': 45.0,
            'power_usage': 2.0
        }
    }
    
    print(f"Publishing block: {json.dumps(test_block, indent=2)}")
    mqtt_client.publish_block(test_block)
    
    # Wait a moment for publishing
    time.sleep(2)
    
    # Disconnect
    mqtt_client.disconnect()
    print("\n✅ Dual broker connection test completed!")
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Expected brokers: 2")
    print(f"Connected brokers: {len(active_brokers)}")
    
    if len(active_brokers) == 2:
        print("✅ SUCCESS: Connected to both MQTT brokers!")
    elif len(active_brokers) == 1:
        print("⚠️  PARTIAL: Connected to only one MQTT broker")
        print("   Check if both brokers are running:")
        print("   - Broker 1: 192.168.2.10:1883")
        print("   - Broker 2: 192.168.2.11:1883")
    else:
        print("❌ FAILED: No MQTT brokers connected")
        print("   Check broker status and network connectivity")
    
    print("\nTo verify messages are being published to both brokers, run:")
    print("mosquitto_sub -h 192.168.2.10 -p 1883 -t 'metrics' -v")
    print("mosquitto_sub -h 192.168.2.11 -p 1883 -t 'metrics' -v")

if __name__ == "__main__":
    test_dual_broker_connection()
