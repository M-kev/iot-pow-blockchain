# Energy-Efficient PoW Blockchain for IoT

This project implements a Proof of Work (PoW) blockchain system optimized for IoT devices, particularly Raspberry Pi. The system uses MQTT for device communication and implements various energy optimization techniques with mathematical models for performance and energy consumption.

## Features

- Proof of Work consensus mechanism with difficulty adjustment
- MQTT-based device communication
- Energy monitoring and optimization
- Raspberry Pi specific optimizations
- Bitcoin-style consensus rules (longest chain, fork resolution, probabilistic finality)
- Real-time dashboard for monitoring
- Mathematical models for performance prediction

## Architecture

### 1. **Blockchain Core**
   - PoW consensus implementation with mathematical models
   - Block mining and validation
   - Transaction processing
   - Energy monitoring and performance modeling

### 2. **MQTT Communication Layer**
   - Device discovery and registration
   - Real-time block and transaction propagation
   - Network status monitoring
   - Miner status broadcasting

### 3. **Energy Management**
   - Real-time power consumption tracking
   - Temperature monitoring
   - CPU and memory usage optimization
   - Power-aware mining decisions

### 4. **Monitoring Dashboard**
   - Real-time blockchain metrics
   - Network node status
   - Energy consumption analytics
   - Mining difficulty and hash rate tracking

## Mathematical Models

### Expected Block Time
```
E[Tblock] = (difficulty × 2^32) / hash_rate
```
Where:
- `difficulty`: Current mining difficulty
- `2^32`: Maximum nonce value
- `hash_rate`: Network hash rate (hashes per second)

### Transaction Throughput
```
TPS = min(tx_per_block / E[Tblock], tx_arrival_rate)
```
Where:
- `tx_per_block`: Number of transactions per block
- `E[Tblock]`: Expected block time
- `tx_arrival_rate`: Transaction arrival rate

### Energy Consumption
```
Eblock = power_draw × E[Tblock]
Etotal = Σ (from i=1 to k) Eblock_i
```
Where:
- `power_draw`: Power consumption in watts
- `E[Tblock]`: Expected block time
- `Etotal`: Total energy over k blocks

## Bitcoin Consensus Rules

### 1. **Consensus Rules (Protocol Standards)**
- Block size limit (1MB like Bitcoin)
- Valid block structure validation
- Valid transaction format verification

### 2. **Proof of Work as Common Metric**
- SHA-256 cryptographic puzzle
- Difficulty adjustment based on block times
- Work calculation for chain comparison

### 3. **Longest Chain Rule (Most Work)**
- Chain selection based on cumulative proof-of-work
- Work-based chain comparison, not length-based
- Automatic chain switching to best chain

### 4. **Temporary Forks and Resolution**
- Automatic fork detection and resolution
- Chain switching to chain with most work
- Orphan block handling

### 5. **Probabilistic Finality**
- 6-confirmation rule for transaction finality
- Block confirmation counting
- Reorganization protection

## Installation

### Prerequisites
- Python 3.8+
- Raspberry Pi (recommended) or Linux system
- MQTT broker (Mosquitto recommended)

### Setup
1. Clone the repository:
```bash
git clone <repository-url>
cd pow-iot-blockchain
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start MQTT broker:
```bash
sudo systemctl start mosquitto
```

## Usage

### Starting a Node
```bash
# Set node ID
export NODE_ID=pi_node_1

# Start the blockchain node
python src/main.py
```

### Accessing Dashboard
Open your browser and navigate to:
- Node 1: http://localhost:8001
- Node 2: http://localhost:8002
- Node 3: http://localhost:8003
- etc.

### Configuration
Edit `config/network_config.py` to configure:
- Node IP addresses
- Dashboard ports
- MQTT broker settings
- Network parameters

## Network Configuration

### Node Setup
The system supports multiple Raspberry Pi nodes:
- `pi_node_1` through `pi_node_6`
- Each node runs independently
- Automatic peer discovery and synchronization

### MQTT Topics
- `blocks`: Block propagation
- `transactions`: Transaction broadcasting
- `metrics`: System metrics sharing
- `network/status`: Network status updates
- `miner/status`: Mining status updates

## Energy Efficiency Features

- Mathematical models for energy consumption and performance
- Dynamic difficulty adjustment based on network hash rate
- Expected block time calculation: E[Tblock] = (difficulty × 2^32) / hash_rate
- Transaction throughput optimization: TPS = min(tx_per_block / E[Tblock], tx_arrival_rate)
- Energy per block calculation: Eblock = power_draw × E[Tblock]
- Optimized mining for low-power devices
- Smart resource allocation
- Power-aware scheduling

## Testing

### Run PoW Tests
```bash
python test_pow.py
```

### Run Bitcoin Consensus Tests
```bash
python test_bitcoin_consensus.py
```

### Test Network
```bash
# Start multiple nodes in different terminals
export NODE_ID=pi_node_1 && python src/main.py
export NODE_ID=pi_node_2 && python src/main.py
export NODE_ID=pi_node_3 && python src/main.py
```

## Monitoring

### Dashboard Features
- Real-time blockchain metrics
- Network node status with online/offline indicators
- Mining difficulty and hash rate tracking
- Chain work and orphan block monitoring
- Individual node performance metrics
- Energy consumption analytics

### Metrics Tracked
- Block count and blockchain size
- Transaction throughput (TPS)
- Mining difficulty and hash rates
- Power consumption and temperature
- CPU and memory usage
- Network synchronization status

## Security Features

### Cryptographic Security
- SHA-256 hash function for PoW
- Block hash verification
- Transaction integrity checks
- Chain validation

### Network Security
- Independent block verification by all nodes
- Fork resolution and chain switching
- Orphan block handling
- Consensus rule enforcement

### Economic Security
- Proof-of-work difficulty adjustment
- 6-confirmation finality rule
- Reorganization protection
- Attack resistance through computational work

## Performance Optimization

### IoT Device Optimization
- Lightweight MQTT communication
- Efficient block validation
- Power-aware mining decisions
- Resource usage monitoring

### Network Optimization
- Automatic peer discovery
- Efficient block propagation
- Fork resolution algorithms
- Chain synchronization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Bitcoin whitepaper and consensus rules
- MQTT protocol for IoT communication
- Raspberry Pi community for hardware optimization
- Energy efficiency research in blockchain systems 