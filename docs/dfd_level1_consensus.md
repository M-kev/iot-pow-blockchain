# Level 1 DFD - DPoS Consensus Mechanism

## Level 1 DFD - Consensus Processes

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    LEVEL 1 DFD - CONSENSUS PROCESSES                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

External Entities:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   System        │    │   MQTT          │    │   HTTP          │    │   User          │
│   Clock         │    │   Network       │    │   Network       │    │   Dashboard     │
│   (Time)        │    │   (Peers)       │    │   (Peers)       │    │   (Browser)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

Data Stores:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Local         │    │   Pending       │    │   Block         │    │   Validator     │
│   Blockchain    │    │   Transactions  │    │   Metrics       │    │   Registry      │
│   (SQLite)      │    │   Pool          │    │   (SQLite)      │    │   (Config)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

Main Processes:

1. VALIDATOR SELECTION PROCESS
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  1.0 Validator Selection                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Get Current   │───▶│   Calculate     │───▶│   Check         │───▶│   Return        │      │
│  │   Time          │    │   Validator     │    │   Validator     │    │   Current       │      │
│  │   (System)      │    │   Index         │    │   Liveness      │    │   Validator     │      │
│  │                 │    │   (Time-based)  │    │   (60s window)  │    │   (Node ID)     │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  Formula: V(t) = delegates[floor(t / block_time) % len(delegates)]                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

2. BLOCK CREATION PROCESS
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  2.0 Block Creation                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Check if      │───▶│   Collect       │───▶│   Create Block  │───▶│   Validate      │      │
│  │   Current       │    │   Pending       │    │   Structure     │    │   Block         │      │
│  │   Validator     │    │   Transactions  │    │   (Header +     │    │   (Hash,        │      │
│  │   (1.0)         │    │   (Pool)        │    │   Body)         │    │   Chain)        │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Calculate     │───▶│   Store Block   │───▶│   Broadcast     │───▶│   Update        │      │
│  │   Block Hash    │    │   (SQLite)      │    │   (MQTT)        │    │   Metrics       │      │
│  │   (SHA-256)     │    │                 │    │                 │    │   (Creation     │      │
│  │                 │    │                 │    │                 │    │   Time)         │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

3. CONSENSUS VALIDATION PROCESS
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  3.0 Consensus Validation                                                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Receive       │───▶│   Validate      │───▶│   Check Chain   │───▶│   Accept/       │      │
│  │   Block         │    │   Block         │    │   Continuity    │    │   Reject        │      │
│  │   (MQTT)        │    │   Structure     │    │   (Previous     │    │   Block         │      │
│  │                 │    │   (Hash,        │    │   Hash)         │    │   (Decision)    │      │
│  │                 │    │   Validator)    │    │                 │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Update        │───▶│   Record        │───▶│   Notify        │───▶│   Continue      │      │
│  │   Local Chain   │    │   Metrics       │    │   Dashboard     │    │   Consensus     │      │
│  │   (SQLite)      │    │   (Consensus    │    │   (Real-time)   │    │   (Next Block)  │      │
│  │                 │    │   Time)         │    │                 │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

4. CHAIN SYNCHRONIZATION PROCESS
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  4.0 Chain Synchronization                                                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Discover      │───▶│   Request       │───▶│   Receive       │───▶│   Validate      │      │
│  │   Peers         │    │   Chain         │    │   Chain Data    │    │   Received      │      │
│  │   (HTTP)        │    │   (HTTP GET)    │    │   (HTTP)        │    │   Chain         │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Compare       │───▶│   Update        │───▶│   Record        │───▶│   Notify        │      │
│  │   Chain         │    │   Local Chain   │    │   Sync Metrics  │    │   Dashboard     │      │
│  │   Lengths       │    │   (If Longer)   │    │   (Sync Time)   │    │   (Chain        │      │
│  │                 │    │                 │    │                 │    │   Status)       │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

Data Flows:
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   Time          │   Validator     │   Pending TXs   │   Block Data    │   Chain Data    │
│   (System)      │   Selection     │   (Pool)        │   (MQTT)        │   (HTTP)        │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

## Level 1 DFD - Consensus Process Details

**Process 1.0: Validator Selection**
- **Input**: Current system time
- **Process**: Calculate validator based on time-based rotation formula
- **Output**: Current validator node ID
- **Data Store**: Validator registry (configuration)

**Process 2.0: Block Creation**
- **Input**: Pending transactions, current validator status
- **Process**: Create block with transactions and energy metrics
- **Output**: New block, broadcast message
- **Data Store**: Local blockchain, block metrics

**Process 3.0: Consensus Validation**
- **Input**: Received block from MQTT
- **Process**: Validate block structure and chain continuity
- **Output**: Accept/reject decision
- **Data Store**: Local blockchain, consensus metrics

**Process 4.0: Chain Synchronization**
- **Input**: Peer discovery via HTTP
- **Process**: Request and validate peer chains
- **Output**: Updated local chain
- **Data Store**: Local blockchain, sync metrics

**Key Consensus Characteristics:**
- **Time-based Rotation**: Deterministic validator selection
- **Single Validator**: Only one node creates blocks at a time
- **MQTT Propagation**: Blocks broadcast via MQTT
- **HTTP Sync**: Chain synchronization via HTTP
- **Energy Metrics**: Each block includes energy consumption data

