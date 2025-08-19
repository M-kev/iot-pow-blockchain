# ... existing code from src/mqtt/client.py ... 

import paho.mqtt.client as mqtt
import json
import time
import threading
from typing import Dict, Any, Callable, Optional
from config.network_config import MQTT_BROKERS, MQTT_TOPICS

class MQTTClient:
    def __init__(self, node_id: str, node_config: Dict[str, Any]):
        self.node_id = node_id
        self.node_config = node_config
        self.client = mqtt.Client()
        self.connected = False
        self.active_broker = None
        self.message_handlers = {}
        
        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Set up reconnection
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
        
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Connected to broker successfully")
            # Subscribe to all topics
            for topic in MQTT_TOPICS.values():
                self.client.subscribe(topic)
                print(f"[MQTT] Subscribed to {topic}")
        else:
            print(f"[MQTT] Connection failed with code {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        self.connected = False
        print(f"[MQTT] Disconnected from broker with code {rc}")
        if rc != 0:
            print("[MQTT] Unexpected disconnection, attempting to reconnect...")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message is received."""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            # Call registered handler for this topic
            if topic in self.message_handlers:
                handler = self.message_handlers[topic]
                handler(payload)
            else:
                print(f"[MQTT] No handler registered for topic: {topic}")
                
        except json.JSONDecodeError as e:
            print(f"[MQTT] Failed to decode message: {e}")
        except Exception as e:
            print(f"[MQTT] Error processing message: {e}")
    
    def connect(self) -> bool:
        """Connect to MQTT broker with fallback."""
        for broker in MQTT_BROKERS:
            try:
                print(f"[MQTT] Attempting to connect to {broker['host']}:{broker['port']}")
                self.client.connect(broker['host'], broker['port'], 60)
                self.active_broker = broker
                
                # Start the network loop in a separate thread
                self.network_thread = threading.Thread(target=self._network_loop, daemon=True)
                self.network_thread.start()
                
                # Wait a bit for connection to establish
                time.sleep(2)
                
                if self.connected:
                    print(f"[MQTT] Successfully connected to {broker['host']}:{broker['port']}")
                    return True
                    
            except Exception as e:
                print(f"[MQTT] Failed to connect to {broker['host']}:{broker['port']}: {e}")
                continue
        
        print("[MQTT] Failed to connect to any broker")
        return False
    
    def _network_loop(self):
        """Network loop for MQTT client."""
        try:
            self.client.loop_forever()
        except Exception as e:
            print(f"[MQTT] Network loop error: {e}")
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.connected:
            self.client.disconnect()
            self.connected = False
            print("[MQTT] Disconnected from broker")
    
    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]):
        """Subscribe to a topic with a message handler."""
        self.message_handlers[topic] = handler
        if self.connected:
            self.client.subscribe(topic)
            print(f"[MQTT] Subscribed to {topic}")
    
    def publish(self, topic: str, message: Dict[str, Any]):
        """Publish a message to a topic."""
        if not self.connected:
            print("[MQTT] Not connected, cannot publish message")
            return
        
        try:
            payload = json.dumps(message)
            result = self.client.publish(topic, payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] Published to {topic}")
            else:
                print(f"[MQTT] Failed to publish to {topic}: {result.rc}")
                
        except Exception as e:
            print(f"[MQTT] Error publishing message: {e}")
    
    def publish_block(self, block_data: Dict[str, Any]):
        """Publish a new block to the network."""
        self.publish(MQTT_TOPICS["BLOCKS"], block_data)
    
    def publish_transaction(self, transaction_data: Dict[str, Any]):
        """Publish a new transaction to the network."""
        self.publish(MQTT_TOPICS["TRANSACTIONS"], transaction_data)
    
    def publish_network_status(self, status_data: Dict[str, Any]):
        """Publish network status to the network."""
        self.publish(MQTT_TOPICS["NETWORK_STATUS"], status_data)
    
    def publish_metrics(self, metrics_data: Dict[str, Any]):
        """Publish device metrics to the network."""
        self.publish(MQTT_TOPICS["METRICS"], metrics_data)
    
    def publish_miner_status(self, status_data: Dict[str, Any]):
        """Publish miner status to the network."""
        self.publish(MQTT_TOPICS["VALIDATOR_STATUS"], status_data)
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get current network status."""
        return {
            'connected': self.connected,
            'active_broker': self.active_broker,
            'node_id': self.node_id,
            'subscribed_topics': list(self.message_handlers.keys())
        } 