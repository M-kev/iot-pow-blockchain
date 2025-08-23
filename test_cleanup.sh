#!/bin/bash

echo "🧪 Testing Cleanup Script..."
echo "============================"

# Create a test directory structure to simulate what setup_node.sh creates
echo "📁 Creating test directory structure..."
mkdir -p ~/iot-pow-blockchain/data
mkdir -p ~/iot-pow-blockchain/blockchain_data
mkdir -p ~/iot-pow-blockchain/static
mkdir -p ~/iot-pow-blockchain/logs
mkdir -p ~/iot-pow-blockchain/venv

# Create test files
echo "📄 Creating test files..."
touch ~/iot-pow-blockchain/data/blockchain_pi_node_1.db
touch ~/iot-pow-blockchain/data/blockchain_pi_node_2.db
touch ~/iot-pow-blockchain/.env
touch ~/iot-pow-blockchain/test_file.log
touch ~/iot-pow-blockchain/test_script.py

# Create Python cache
echo "🐍 Creating Python cache files..."
mkdir -p ~/iot-pow-blockchain/src/__pycache__
touch ~/iot-pow-blockchain/src/__pycache__/test.pyc

echo ""
echo "✅ Test environment created!"
echo "   - Test directories: ~/iot-pow-blockchain/"
echo "   - Test databases: blockchain_pi_node_1.db, blockchain_pi_node_2.db"
echo "   - Test files: .env, test_file.log, test_script.py"
echo "   - Python cache: __pycache__ directory"
echo ""
echo "🧹 Now testing cleanup script..."
echo "================================"

# Run the cleanup script (but don't actually remove the repository)
echo "Note: When prompted, choose 'n' to preserve the repository directory"
echo ""

# Make the cleanup script executable and run it
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh

echo ""
echo "🧪 Cleanup Test Complete!"
echo "========================="
echo "Check if the following were cleaned up:"
echo "   - Test databases removed"
echo "   - Test files removed"
echo "   - Python cache removed"
echo "   - Environment file removed"
echo "   - Virtual environment removed"
echo ""
echo "💡 The cleanup script should now be ready for production use!"
