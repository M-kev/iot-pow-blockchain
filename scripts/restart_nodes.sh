#!/bin/bash

echo "Restarting PoW blockchain nodes..."

# Function to restart a specific node
restart_node() {
    local node_num=$1
    local node_id="pi_node_$node_num"
    local ip="192.168.2.10$(($node_num + 105))"
    
    echo "Restarting $node_id on $ip..."
    
    # SSH to the node and restart the service
    ssh pi@$ip << EOF
        echo "Stopping blockchain service on $node_id..."
        sudo systemctl stop blockchain-node
        
        echo "Pulling latest code on $node_id..."
        cd ~/iot-pow-blockchain
        git pull
        
        echo "Updating Python dependencies on $node_id..."
        source venv/bin/activate
        pip install -r requirements.txt
        
        echo "Starting blockchain service on $node_id..."
        sudo systemctl start blockchain-node
        
        echo "Checking service status on $node_id..."
        sudo systemctl status blockchain-node --no-pager
EOF
    
    echo "Node $node_id restart completed!"
    echo "Dashboard available at: http://$ip:800$node_num"
    echo "---"
}

# Restart all nodes
for i in {1..6}; do
    restart_node $i
done

echo "All nodes have been restarted with updated PoW code!"
echo ""
echo "Monitor node logs with:"
echo "  sudo journalctl -u blockchain-node -f"
echo ""
echo "Check node status with:"
echo "  sudo systemctl status blockchain-node"
