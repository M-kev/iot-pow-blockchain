#!/bin/bash

# Check if node number is provided
if [ -z "$1" ]; then
    echo "Please provide node number (1-6)"
    exit 1
fi

NODE_NUM=$1
if [ $NODE_NUM -lt 1 ] || [ $NODE_NUM -gt 6 ]; then
    echo "Node number must be between 1 and 6"
    exit 1
fi

# Set the node ID based on the node number
NODE_ID="pi_node_$NODE_NUM"
echo "Setting up PoW blockchain node: $NODE_ID"

REPO_URL=https://github.com/M-kev/iot-pow-blockchain.git  # Updated for PoW
REPO_DIR="$HOME/iot-pow-blockchain"

# Clone the repository if not already present
if [ ! -d "$REPO_DIR/.git" ]; then
    git clone $REPO_URL $REPO_DIR
fi

cd $REPO_DIR

echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p ~/iot-pow-blockchain/blockchain_data
mkdir -p ~/iot-pow-blockchain/static
mkdir -p ~/iot-pow-blockchain/data  # For SQLite database

# Set proper permissions
chmod -R 755 ~/iot-pow-blockchain
chown -R $USER:$USER ~/iot-pow-blockchain

# Ensure the data directory is writable
chmod 777 ~/iot-pow-blockchain/data

# Create an empty database file to ensure proper permissions
touch ~/iot-pow-blockchain/data/blockchain.db
chmod 666 ~/iot-pow-blockchain/data/blockchain.db

# Create .env file with the correct NODE_ID
echo "Creating .env file with NODE_ID=$NODE_ID"
cat > ~/iot-pow-blockchain/.env << EOF
NODE_ID=$NODE_ID
MQTT_BROKER_HOST=192.168.2.10
MQTT_BROKER_PORT=1883
EOF

# Create systemd service file
sudo tee /etc/systemd/system/blockchain-node.service > /dev/null << EOF
[Unit]
Description=PoW Blockchain Node Service
After=network.target

[Service]
User=$USER
WorkingDirectory=$HOME/iot-pow-blockchain
Environment="PATH=$HOME/iot-pow-blockchain/venv/bin:/usr/bin"
Environment="PYTHONPATH=$HOME/iot-pow-blockchain:$HOME/iot-pow-blockchain/src"
Environment="NODE_ID=$NODE_ID"
ExecStart=$HOME/iot-pow-blockchain/venv/bin/python $HOME/iot-pow-blockchain/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable blockchain-node
sudo systemctl start blockchain-node

# Check service status
sudo systemctl status blockchain-node

echo "PoW blockchain node setup complete for $NODE_ID!"
echo "Dashboard available at: http://192.168.2.10$(($NODE_NUM + 105)):800$NODE_NUM" 
