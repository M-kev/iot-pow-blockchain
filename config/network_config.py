import os
from typing import Dict, Any, Optional

# Network Settings
NETWORK_SETTINGS = {
    'timeout': 30,
    'retry_attempts': 3,
    'sync_interval': 60,  # seconds
    'metrics_interval': 5,  # seconds
}

# Raspberry Pi Specific Settings
RASPBERRY_PI_SETTINGS = {
    'cpu_throttle_temp': 80.0,  # Celsius
    'max_cpu_usage': 90.0,  # percentage
    'max_memory_usage': 85.0,  # percentage
    'power_threshold': 5.0,  # watts
    'metrics_interval': 5,  # seconds
    'sync_interval': 60,  # seconds
}

# MQTT Broker Configuration
MQTT_BROKERS = [
    {
        'host': os.getenv('MQTT_BROKER_HOST', 'localhost'),
        'port': int(os.getenv('MQTT_BROKER_PORT', 1883)),
        'username': os.getenv('MQTT_BROKER_USERNAME', None),
        'password': os.getenv('MQTT_BROKER_PASSWORD', None)
    }
]

# Raspberry Pi Nodes Configuration
RASPBERRY_PI_NODES = [
    {
        "id": "pi_node_1",
        "ip": os.getenv("PI_NODE_1_IP", "192.168.2.106"),
        "dashboard_port": 8001,
        "hash_rate": 1000,  # Estimated hash rate in H/s
    },
    {
        "id": "pi_node_2",
        "ip": os.getenv("PI_NODE_2_IP", "192.168.2.107"),
        "dashboard_port": 8002,
        "hash_rate": 1000,  # Estimated hash rate in H/s
    },
    {
        "id": "pi_node_3",
        "ip": os.getenv("PI_NODE_3_IP", "192.168.2.104"),
        "dashboard_port": 8003,
        "hash_rate": 1000,  # Estimated hash rate in H/s
    },
    {
        "id": "pi_node_4",
        "ip": os.getenv("PI_NODE_4_IP", "192.168.2.102"),
        "dashboard_port": 8004,
        "hash_rate": 1000,  # Estimated hash rate in H/s
    },
    {
        "id": "pi_node_5",
        "ip": os.getenv("PI_NODE_5_IP", "192.168.2.105"),
        "dashboard_port": 8005,
        "hash_rate": 1000,  # Estimated hash rate in H/s
    },
    {
        "id": "pi_node_6",
        "ip": os.getenv("PI_NODE_6_IP", "192.168.2.101"),
        "dashboard_port": 8006,
        "hash_rate": 1000,  # Estimated hash rate in H/s
    }
]

# MQTT Topics
MQTT_TOPICS = {
    "BLOCKS": "blocks",
    "TRANSACTIONS": "transactions",
    "METRICS": "metrics",
    "NETWORK_STATUS": "network/status",
    "MINER_STATUS": "miner/status"  # Updated key name for consistency
}

def get_node_config(node_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific node."""
    for node in RASPBERRY_PI_NODES:
        if node['id'] == node_id:
            return node
    return None 