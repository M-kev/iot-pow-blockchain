# PoW Blockchain Network Deployment Guide

This guide provides step-by-step instructions for deploying the energy-efficient PoW blockchain network with 6 Raspberry Pi nodes and MQTT broker.

## Prerequisites

### For MQTT Broker
- Ubuntu Server 20.04 LTS or later
- 2GB RAM minimum
- 20GB storage
- Static IP address (192.168.2.10)

### For Raspberry Pi Nodes
- Raspberry Pi 4 (2GB RAM or more)
- Raspberry Pi OS (64-bit)
- MicroSD card (32GB recommended)
- Power supply
- Network connection
- `python3-dev` (required for some Python packages)

## Network Setup

1. Configure static IP addresses for all devices:
   - MQTT Broker: 192.168.2.10
   - Raspberry Pi 1: 192.168.2.106
   - Raspberry Pi 2: 192.168.2.107
   - Raspberry Pi 3: 192.168.2.104
   - Raspberry Pi 4: 192.168.2.102
   - Raspberry Pi 5: 192.168.2.105
   - Raspberry Pi 6: 192.168.2.101

2. Ensure all devices can communicate with each other:
   ```bash
   ping 192.168.2.10  # From all devices
   ```

## MQTT Broker Deployment

1. SSH into the MQTT broker VM:
   ```bash
   ssh user@192.168.2.10
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/M-kev/iot-pow-blockchain.git
   cd pow-iot-blockchain
   ```

3. Make the setup script executable:
   ```bash
   chmod +x scripts/setup_broker.sh
   ```

4. Run the setup script:
   ```bash
   ./scripts/setup_broker.sh
   ```

5. Verify MQTT broker status:
   ```bash
   sudo systemctl status mosquitto
   ```

## Raspberry Pi Node Deployment

1. SSH into each Raspberry Pi:
   ```bash
   ssh pi@192.168.2.10X  # Where X is 1-6
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/M-kev/iot-pow-blockchain.git
   cd pow-iot-blockchain
   ```

3. Make the setup script executable:
   ```bash
   chmod +x scripts/setup_node.sh
   ```

4. Run the setup script for each node:
   ```bash
   # On Raspberry Pi 1
   ./scripts/setup_node.sh 1

   # On Raspberry Pi 2
   ./scripts/setup_node.sh 2

   # And so on for nodes 3-6
   ```

5. Verify node status:
   ```bash
   sudo systemctl status blockchain-node
   ```

## Testing the Deployment

1. Check MQTT broker connectivity:
   ```bash
   # On any Raspberry Pi
   mosquitto_sub -h 192.168.2.10 -p 1883 -t 'blocks'
   mosquitto_sub -h 192.168.2.10 -p 1883 -t 'miner/status'
   ```

2. Access node dashboards:
   - Node 1: http://192.168.2.106:8001
   - Node 2: http://192.168.2.107:8002
   - Node 3: http://192.168.2.104:8003
   - Node 4: http://192.168.2.102:8004
   - Node 5: http://192.168.2.105:8005
   - Node 6: http://192.168.2.101:8006

3. Monitor node logs:
   ```bash
   sudo journalctl -u blockchain-node -f
   ```

## PoW-Specific Features

### Mining Configuration
- Each node can mine blocks independently
- Difficulty automatically adjusts based on network hash rate
- Target block time: 3 seconds
- Energy monitoring prevents overheating

### Consensus Rules
- Bitcoin-style consensus with longest chain rule
- Fork resolution based on cumulative proof-of-work
- 6-confirmation finality for transactions
- 1MB block size limit

### Mathematical Models
- Expected block time: `E[Tblock] = (difficulty × 2^32) / hash_rate`
- Transaction throughput: `TPS = min(tx_per_block / E[Tblock], tx_arrival_rate)`
- Energy consumption: `Eblock = power_draw × E[Tblock]`

## Troubleshooting

1. MQTT Connection Issues:
   - Check broker status: `sudo systemctl status mosquitto`
   - Verify network connectivity
   - Review broker logs: `sudo tail -f /var/log/mosquitto/mosquitto.log`

2. Node Issues:
   - Check node status: `sudo systemctl status blockchain-node`
   - Review node logs: `sudo journalctl -u blockchain-node`
   - Verify Python environment: `source venv/bin/activate && python --version`
   - Check system resources: `htop`

3. Mining Issues:
   - Check difficulty settings in dashboard
   - Monitor hash rate and power consumption
   - Verify block validation and propagation

4. Dashboard Access Issues:
   - Verify port accessibility: `netstat -tulpn | grep 800`
   - Check firewall settings: `sudo ufw status`
   - Verify node is running: `sudo systemctl status blockchain-node`

## Maintenance

1. Updating Nodes:
   ```bash
   cd ~/pow-iot-blockchain
   git pull
   source venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart blockchain-node
   ```

2. Updating Broker:
   ```bash
   sudo apt-get update
   sudo apt-get upgrade mosquitto
   sudo systemctl restart mosquitto
   ```

3. Backup:
   - Regularly backup node data
   - Monitor system resources
   - Check logs for errors

## Security Notes

1. Change default passwords
2. Use SSH keys for authentication
3. Keep systems updated
4. Monitor system logs
5. Use firewall rules to restrict access 