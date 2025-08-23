#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import requests
import time
from config.network_config import RASPBERRY_PI_NODES

def test_network_status():
    """Test which nodes are running and accessible."""
    
    print("Testing Network Node Status...")
    print("=" * 50)
    
    active_nodes = []
    inactive_nodes = []
    
    for node in RASPBERRY_PI_NODES:
        node_id = node['id']
        ip = node['ip']
        port = node['dashboard_port']
        url = f"http://{ip}:{port}/api/metrics"
        
        print(f"\nTesting {node_id} at {ip}:{port}")
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ {node_id} is ACTIVE")
                print(f"     Consensus: {data.get('consensus_protocol', 'Unknown')}")
                print(f"     Total Blocks: {data.get('blockchain_metrics', {}).get('total_blocks', 'Unknown')}")
                print(f"     System Metrics: {len(data.get('system_metrics', {}))} nodes")
                
                # Check if this node has metrics from other nodes
                system_metrics = data.get('system_metrics', {})
                other_nodes = [n for n in system_metrics.keys() if n != node_id]
                if other_nodes:
                    print(f"     Connected to: {', '.join(other_nodes)}")
                else:
                    print(f"     ⚠️  No other nodes detected")
                
                active_nodes.append(node_id)
            else:
                print(f"  ❌ {node_id} returned status {response.status_code}")
                inactive_nodes.append(node_id)
                
        except requests.exceptions.ConnectionError:
            print(f"  ❌ {node_id} connection failed")
            inactive_nodes.append(node_id)
        except requests.exceptions.Timeout:
            print(f"  ❌ {node_id} timeout")
            inactive_nodes.append(node_id)
        except Exception as e:
            print(f"  ❌ {node_id} error: {e}")
            inactive_nodes.append(node_id)
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Active nodes: {len(active_nodes)} - {', '.join(active_nodes) if active_nodes else 'None'}")
    print(f"Inactive nodes: {len(inactive_nodes)} - {', '.join(inactive_nodes) if inactive_nodes else 'None'}")
    
    if len(active_nodes) == 1:
        print("\n⚠️  Only one node is active. This explains why you only see data from one node.")
        print("   Make sure all nodes are started with: ./scripts/restart_nodes.sh")
    elif len(active_nodes) > 1:
        print("\n✅ Multiple nodes are active. Check MQTT communication if data isn't shared.")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_network_status()
