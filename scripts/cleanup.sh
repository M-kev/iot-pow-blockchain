#!/bin/bash

echo "🧹 Starting PoW Blockchain Node Cleanup..."
echo "=========================================="

# Stop the blockchain service
echo "📋 Stopping blockchain service..."
sudo systemctl stop blockchain-node 2>/dev/null || echo "   Service not running or not found"

# Disable the service
echo "📋 Disabling blockchain service..."
sudo systemctl disable blockchain-node 2>/dev/null || echo "   Service not found"

# Remove the systemd service file
echo "📋 Removing systemd service file..."
sudo rm -f /etc/systemd/system/blockchain-node.service

# Reload systemd
echo "📋 Reloading systemd..."
sudo systemctl daemon-reload

# Remove blockchain data directories
echo "🗂️  Removing blockchain data directories..."
rm -rf ~/iot-pow-blockchain/data/blockchain_*.db
rm -rf ~/iot-pow-blockchain/blockchain_data
rm -rf ~/iot-pow-blockchain/static
rm -rf ~/iot-pow-blockchain/logs

# Remove SQLite databases (node-specific and general)
echo "🗄️  Removing SQLite databases..."
rm -f ~/iot-pow-blockchain/data/blockchain.db
rm -f ~/iot-pow-blockchain/data/blockchain_*.db

# Remove any temporary files
echo "🗑️  Cleaning temporary files..."
rm -f ~/iot-pow-blockchain/*.log
rm -f ~/iot-pow-blockchain/*.pid
rm -f ~/iot-pow-blockchain/logs/*.log 2>/dev/null

# Remove environment file
echo "🗑️  Removing environment configuration..."
rm -f ~/iot-pow-blockchain/.env

# Remove any Python cache files
echo "🗑️  Cleaning Python cache..."
find ~/iot-pow-blockchain -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find ~/iot-pow-blockchain -name "*.pyc" -delete 2>/dev/null

# Remove any test files that might have been created
echo "🗑️  Cleaning test files..."
rm -f ~/iot-pow-blockchain/test_*.py
rm -f ~/iot-pow-blockchain/*_test.py

# Remove virtual environment
echo "🗑️  Removing Python virtual environment..."
rm -rf ~/iot-pow-blockchain/venv

# Remove the entire repository directory (optional)
echo "🗑️  Do you want to remove the entire repository directory? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "   Removing repository directory..."
    rm -rf ~/iot-pow-blockchain
    echo "   Repository directory removed"
else
    echo "   Repository directory preserved"
fi

# Check if MQTT brokers are running and offer to stop them
echo "📡 Checking MQTT broker status..."
if pgrep mosquitto > /dev/null; then
    echo "   MQTT broker(s) detected. Do you want to stop them? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "   Stopping MQTT brokers..."
        sudo pkill mosquitto
        sudo systemctl stop mosquitto 2>/dev/null
    fi
else
    echo "   No MQTT brokers running"
fi

# Show what was cleaned up
echo ""
echo "✅ Cleanup Summary:"
echo "   - Stopped and disabled blockchain service"
echo "   - Removed systemd service file"
echo "   - Removed all blockchain databases (node-specific and general)"
echo "   - Removed data directories and static files"
echo "   - Cleaned temporary, cache, and test files"
echo "   - Removed environment configuration"
echo "   - Removed Python virtual environment"
echo "   - Cleaned Python cache files"

echo ""
echo "🎯 Cleanup complete! You can now redeploy the node using:"
echo "   ./scripts/setup_node.sh"
echo ""
echo "💡 To start fresh on this node, run:"
echo "   git clone https://github.com/M-kev/iot-pow-blockchain.git"
echo "   cd iot-pow-blockchain"
echo "   ./scripts/setup_node.sh" 