#!/bin/bash

# Check if broker number is provided
if [ -z "$1" ]; then
    echo "Please provide broker number (1 or 2)"
    echo "Usage: ./setup_broker.sh 1  # For broker at 192.168.2.10"
    echo "Usage: ./setup_broker.sh 2  # For broker at 192.168.2.11"
    exit 1
fi

BROKER_NUM=$1
if [ $BROKER_NUM -eq 1 ]; then
    BROKER_IP="192.168.2.10"
elif [ $BROKER_NUM -eq 2 ]; then
    BROKER_IP="192.168.2.11"
else
    echo "Invalid broker number. Must be 1 or 2."
    exit 1
fi

echo "Setting up MQTT broker $BROKER_NUM for PoW blockchain network at $BROKER_IP..."

# Install Mosquitto MQTT broker
sudo apt-get update
sudo apt-get install -y mosquitto mosquitto-clients

# Create configuration directory
sudo mkdir -p /etc/mosquitto/conf.d

# Create broker configuration (simplified for PoW)
sudo tee /etc/mosquitto/conf.d/broker.conf << EOF
listener 1883
allow_anonymous true
bind_address $BROKER_IP
EOF

# Set proper permissions
sudo chown -R mosquitto:mosquitto /etc/mosquitto

# Restart Mosquitto service
sudo systemctl restart mosquitto

# Enable Mosquitto to start on boot
sudo systemctl enable mosquitto

# Verify service status
sudo systemctl status mosquitto

echo "MQTT broker $BROKER_NUM setup complete for PoW blockchain!"
echo "Broker running on: $BROKER_IP:1883" 