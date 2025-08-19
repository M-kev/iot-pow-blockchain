#!/bin/bash

echo "Setting up MQTT broker for PoW blockchain network..."

# Install Mosquitto MQTT broker
sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients

# Create configuration directory
sudo mkdir -p /etc/mosquitto/conf.d

# Create broker configuration (simplified for PoW)
sudo tee /etc/mosquitto/conf.d/broker.conf << EOF
listener 1883
allow_anonymous true
EOF

# Set proper permissions
sudo chown -R mosquitto:mosquitto /etc/mosquitto

# Restart Mosquitto service
sudo systemctl restart mosquitto

# Enable Mosquitto to start on boot
sudo systemctl enable mosquitto

# Verify service status
sudo systemctl status mosquitto

echo "MQTT broker setup complete for PoW blockchain!"
echo "Broker running on: 192.168.2.10:1883" 