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
        self.clients = []  # Multiple MQTT clients for redundancy
        self.connected = False
        self.active_brokers = []  # Track all connected brokers
        self.message_handlers = {}
        
        # Create MQTT clients for each broker
        for i, broker in enumerate(MQTT_BROKERS):
            client = mqtt.Client()
            client.on_connect = lambda client, userdata, flags, rc, broker_index=i: self._on_connect(client, userdata, flags, rc, broker_index)
            client.on_message = self._on_message
            client.on_disconnect = lambda client, userdata, rc, broker_index=i: self._on_disconnect(client, userdata, rc, broker_index)
            
            # Set up reconnection
            client.reconnect_delay_set(min_delay=1, max_delay=120)
            
            self.clients.append(client)
        
    def _on_connect(self, client, userdata, flags, rc, broker_index):
        """Callback when connected to MQTT broker."""
        broker = MQTT_BROKERS[broker_index]
        if rc == 0:
            self.connected = True
            self.active_brokers.append(broker)
            print(f"[MQTT] Connected to broker {broker_index + 1} ({broker['host']}:{broker['port']}) successfully")
            # Subscribe to all topics
            for topic in MQTT_TOPICS.values():
                client.subscribe(topic)
                print(f"[MQTT] Subscribed to {topic} on broker {broker_index + 1}")
        else:
            print(f"[MQTT] Connection to broker {broker_index + 1} failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc, broker_index):
        """Callback when disconnected from MQTT broker."""
        broker = MQTT_BROKERS[broker_index]
        if broker in self.active_brokers:
            self.active_brokers.remove(broker)
        if not self.active_brokers:
            self.connected = False
        print(f"[MQTT] Disconnected from broker {broker_index + 1} ({broker['host']}:{broker['port']}) with code {rc}")
        if rc != 0:
            print(f"[MQTT] Unexpected disconnection from broker {broker_index + 1}, attempting to reconnect...")
    
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
        """Connect to all MQTT brokers for redundancy."""
        network_threads = []
        
        for i, broker in enumerate(MQTT_BROKERS):
            try:
                print(f"[MQTT] Attempting to connect to broker {i + 1}: {broker['host']}:{broker['port']}")
                print(f"[MQTT] Broker config: {broker}")
                
                client = self.clients[i]
                client.connect(broker['host'], broker['port'], 60)
                
                # Start the network loop in a separate thread for each client
                network_thread = threading.Thread(target=self._network_loop, args=(client,), daemon=True)
                network_thread.start()
                network_threads.append(network_thread)
                
            except Exception as e:
                print(f"[MQTT] Failed to connect to broker {i + 1} ({broker['host']}:{broker['port']}): {e}")
                continue
        
        # Wait a bit for connections to establish
        time.sleep(3)
        
        if self.connected:
            print(f"[MQTT] Successfully connected to {len(self.active_brokers)} broker(s)")
            for broker in self.active_brokers:
                print(f"[MQTT] Active broker: {broker['host']}:{broker['port']}")
            return True
        else:
            print("[MQTT] Failed to connect to any broker")
            return False
    
    def _network_loop(self, client):
        """Network loop for MQTT client."""
        try:
            client.loop_forever()
        except Exception as e:
            print(f"[MQTT] Network loop error: {e}")
    
    def disconnect(self):
        """Disconnect from all MQTT brokers."""
        for client in self.clients:
            try:
                client.disconnect()
            except:
                pass
        self.connected = False
        self.active_brokers.clear()
        print("[MQTT] Disconnected from all brokers")
    
    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]):
        """Subscribe to a topic with a message handler on all brokers."""
        self.message_handlers[topic] = handler
        if self.connected:
            for client in self.clients:
                try:
                    client.subscribe(topic)
                    print(f"[MQTT] Subscribed to {topic} on all brokers")
                except Exception as e:
                    print(f"[MQTT] Failed to subscribe to {topic}: {e}")
    
    def publish(self, topic: str, message: Dict[str, Any]):
        """Publish a message to a topic on all connected brokers."""
        if not self.connected:
            print(f"[MQTT] Not connected, cannot publish message to {topic}")
            return
        
        try:
            payload = json.dumps(message)
            published_count = 0
            
            for client in self.clients:
                try:
                    result = client.publish(topic, payload)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        published_count += 1
                except Exception as e:
                    print(f"[MQTT] Failed to publish to {topic} on one broker: {e}")
            
            if published_count > 0:
                print(f"[MQTT] Published to {topic} on {published_count} broker(s): {len(payload)} bytes")
            else:
                print(f"[MQTT] Failed to publish to {topic} on any broker")
                
        except Exception as e:
            print(f"[MQTT] Error publishing message to {topic}: {e}")
    
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
        self.publish(MQTT_TOPICS["MINER_STATUS"], status_data)
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get current network status."""
        return {
            'connected': self.connected,
            'active_brokers': [f"{broker['host']}:{broker['port']}" for broker in self.active_brokers],
            'node_id': self.node_id,
            'subscribed_topics': list(self.message_handlers.keys())
        } 