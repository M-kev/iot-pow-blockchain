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
REPO_DIR="$HOME/pow-iot-blockchain"

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
mkdir -p ~/pow-iot-blockchain/blockchain_data
mkdir -p ~/pow-iot-blockchain/static
mkdir -p ~/pow-iot-blockchain/data  # For SQLite database

# Set proper permissions
chmod -R 755 ~/pow-iot-blockchain
chown -R $USER:$USER ~/pow-iot-blockchain

# Ensure the data directory is writable
chmod 777 ~/pow-iot-blockchain/data

# Create an empty database file to ensure proper permissions
touch ~/pow-iot-blockchain/data/blockchain.db
chmod 666 ~/pow-iot-blockchain/data/blockchain.db

# Create .env file with the correct NODE_ID
echo "Creating .env file with NODE_ID=$NODE_ID"
cat > ~/pow-iot-blockchain/.env << EOF
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
WorkingDirectory=$HOME/pow-iot-blockchain
Environment="PATH=$HOME/pow-iot-blockchain/venv/bin:/usr/bin"
Environment="PYTHONPATH=$HOME/pow-iot-blockchain:$HOME/pow-iot-blockchain/src"
Environment="NODE_ID=$NODE_ID"
ExecStart=$HOME/pow-iot-blockchain/venv/bin/python $HOME/pow-iot-blockchain/src/main.py
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
