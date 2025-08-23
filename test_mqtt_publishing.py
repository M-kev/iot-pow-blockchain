#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from network.mqtt_client import MQTTClient
from config.network_config import get_node_config, MQTT_TOPICS
import time
import json

def test_mqtt_publishing():
    """Test MQTT connection and publishing."""
    
    print("Testing MQTT Publishing...")
    
    # Test with Node 1 configuration
    node_id = "pi_node_1"
    node_config = get_node_config(node_id)
    
    if not node_config:
        print(f"❌ Node config not found for {node_id}")
        return
    
    print(f"Testing with {node_id} config: {node_config}")
    
    # Create MQTT client
    mqtt_client = MQTTClient(node_id, node_config)
    
    # Try to connect
    print("\nAttempting to connect to MQTT broker...")
    connection_result = mqtt_client.connect()
    
    if not connection_result:
        print("❌ Failed to connect to MQTT broker")
        return
    
    print("✅ Connected to MQTT broker")
    
    # Wait a moment for connection to stabilize
    time.sleep(3)
    
    # Test publishing metrics
    print("\nTesting metrics publishing...")
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
    
    # Test publishing a block
    print("\nTesting block publishing...")
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
    
    # Test publishing miner status
    print("\nTesting miner status publishing...")
    test_status = {
        'node_id': node_id,
        'block_count': 5,
        'hash_rate': 1000,
        'difficulty': 1,
        'mining_time': 3.2
    }
    
    print(f"Publishing miner status: {json.dumps(test_status, indent=2)}")
    mqtt_client.publish_miner_status(test_status)
    
    # Wait a moment for publishing
    time.sleep(2)
    
    # Get network status
    network_status = mqtt_client.get_network_status()
    print(f"\nNetwork status: {json.dumps(network_status, indent=2)}")
    
    # Disconnect
    mqtt_client.disconnect()
    print("\n✅ MQTT publishing test completed!")
    
    print("\nTo verify messages are being published, run:")
    print("mosquitto_sub -h 192.168.2.10 -p 1883 -t 'metrics' -v")
    print("mosquitto_sub -h 192.168.2.10 -p 1883 -t 'blocks' -v")
    print("mosquitto_sub -h 192.168.2.10 -p 1883 -t 'miner/status' -v")

if __name__ == "__main__":
    test_mqtt_publishing()
