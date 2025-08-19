# Level 2 DFD - Transaction Processing Flow

## Level 2 DFD - Detailed Transaction Processing

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    LEVEL 2 DFD - TRANSACTION PROCESSING                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

External Entities:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   System        │    │   MQTT          │    │   Energy        │    │   User          │
│   Monitor       │    │   Network       │    │   Sensors       │    │   Dashboard     │
│   (psutil)      │    │   (Peers)       │    │   (Hardware)    │    │   (Browser)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

Data Stores:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Transaction   │    │   Block         │    │   Energy        │    │   System        │
│   Lifecycle     │    │   Metrics       │    │   Metrics       │    │   Metrics       │
│   (SQLite)      │    │   (SQLite)      │    │   (Memory)      │    │   (Memory)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

Detailed Processes:

1. METRICS COLLECTION PROCESS
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  1.1 System Metrics Collection                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   CPU Usage     │───▶│   Memory Usage  │───▶│   Temperature   │───▶│   Power Usage   │      │
│  │   (psutil.cpu_  │    │   (psutil.virt_ │    │   (psutil.sens_ │    │   (Custom       │      │
│  │   _percent)     │    │   ual_memory)   │    │   ors_temperat) │    │   calculation)  │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Aggregate     │───▶│   Add           │───▶│   Store in      │───▶│   Ready for     │      │
│  │   Metrics       │    │   Timestamp     │    │   Memory        │    │   MQTT          │      │
│  │   (All values)  │    │   (time.time()) │    │   (metrics)     │    │   Publishing    │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

2. MQTT PUBLISHING PROCESS
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  1.2 MQTT Metrics Publishing                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Get Metrics   │───▶│   Format        │───▶│   Connect to    │───▶│   Publish to    │      │
│  │   from Memory   │    │   JSON          │    │   MQTT Broker   │    │   Topic         │      │
│  │   (metrics)     │    │   (json.dumps)  │    │   (paho-mqtt)   │    │   (iot/metrics) │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Handle        │───▶│   Retry on      │───▶│   Log           │───▶│   Continue      │      │
│  │   Connection    │    │   Failure       │    │   Success/      │    │   (Next         │      │
│  │   Errors        │    │   (Broker 2)    │    │   Error         │    │   Publish)      │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

3. TRANSACTION CREATION PROCESS
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  2.1 Incoming Metrics to Transaction Conversion                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Receive       │───▶│   Parse JSON    │───▶│   Extract       │───▶│   Generate      │      │
│  │   MQTT Message  │    │   (json.loads)  │    │   Node ID       │    │   Transaction   │      │
│  │   (iot/metrics) │    │                 │    │   and Metrics   │    │   Hash          │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Create        │───▶│   Record        │───▶│   Add to        │───▶│   Update        │      │
│  │   Transaction   │    │   Received      │    │   Pending Pool  │    │   TPS Counter   │      │
│  │   Object        │    │   Timestamp     │    │   (pending_txs) │    │   (metrics)     │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

4. TRANSACTION POOL MANAGEMENT
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  2.2 Pending Transaction Pool Management                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Check Pool    │───▶│   Validate      │───▶│   Remove        │───▶│   Update        │      │
│  │   Size          │    │   Transaction   │    │   Duplicates    │    │   Pool Status   │      │
│  │   (len)         │    │   (Structure)   │    │   (Hash check)  │    │   (Dashboard)   │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Check         │───▶│   Prioritize    │───▶│   Limit Pool    │───▶│   Ready for     │      │
│  │   Transaction   │    │   by Timestamp  │    │   Size          │    │   Block         │      │
│  │   Age           │    │   (Oldest       │    │   (Max 1000)    │    │   Creation      │      │
│  │                 │    │   First)        │    │                 │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

5. BLOCK TRANSACTION INCLUSION
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  2.3 Transaction Inclusion in Block                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Check if      │───▶│   Select        │───▶│   Create Block  │───▶│   Include       │      │
│  │   Current       │    │   Transactions  │    │   Header        │    │   Transactions  │      │
│  │   Validator     │    │   from Pool     │    │   (block_index, │    │   in Block      │      │
│  │   (1.0)         │    │   (Up to 100)   │    │   timestamp,    │    │   Body          │      │
│  │                 │    │                 │    │   previous_hash)│    │   (transactions)│      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Calculate     │───▶│   Store Block   │───▶│   Update        │───▶│   Clear         │      │
│  │   Block Hash    │    │   in Database   │    │   Transaction   │    │   Included      │      │
│  │   (SHA-256)     │    │   (SQLite)      │    │   Lifecycle     │    │   Transactions  │      │
│  │                 │    │                 │    │   (included_    │    │   from Pool     │      │
│  │                 │    │                 │    │   timestamp)    │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

6. TRANSACTION LIFECYCLE TRACKING
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  2.4 Transaction Lifecycle Database Operations                                                    │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Record        │───▶│   Update        │───▶│   Calculate     │───▶│   Store          │      │
│  │   Received      │    │   Included      │    │   Latency       │    │   Lifecycle     │      │
│  │   Timestamp     │    │   Timestamp     │    │   (included -   │    │   Data          │      │
│  │   (INSERT)      │    │   (UPDATE)      │    │   received)     │    │   (SQLite)      │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Handle        │───▶│   Log           │───▶│   Update        │───▶│   Ready for     │      │
│  │   Missing       │    │   Transaction   │    │   Dashboard     │    │   Analytics     │      │
│  │   Timestamps    │    │   Events        │    │   Metrics       │    │   Export        │      │
│  │   (COALESCE)    │    │   (Debug)       │    │   (Real-time)   │    │   (CSV)         │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

Data Flows:
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   System        │   MQTT          │   Transaction   │   Block         │   Lifecycle     │
│   Metrics       │   Messages      │   Objects       │   Data          │   Data          │
│   (CPU, Mem,    │   (JSON)        │   (Hash, Type,  │   (Header,      │   (Received,    │
│   Temp, Power)  │                 │   Node ID,      │   Body, Hash)   │   Included,     │
│                 │                 │   Metrics)      │                 │   Latency)      │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

## Level 2 DFD - Transaction Processing Details

**Process 1.1: System Metrics Collection**
- **Input**: Hardware sensors and system calls
- **Process**: Collect CPU, memory, temperature, and power usage
- **Output**: Aggregated metrics with timestamp
- **Data Store**: System metrics (memory)

**Process 1.2: MQTT Metrics Publishing**
- **Input**: Aggregated system metrics
- **Process**: Format as JSON and publish to MQTT broker
- **Output**: MQTT message on iot/metrics topic
- **Data Store**: None (network transmission)

**Process 2.1: Incoming Metrics to Transaction Conversion**
- **Input**: MQTT message from other nodes
- **Process**: Parse JSON, extract data, generate transaction hash
- **Output**: Transaction object added to pending pool
- **Data Store**: Transaction lifecycle (received timestamp)

**Process 2.2: Pending Transaction Pool Management**
- **Input**: New transactions and pool state
- **Process**: Validate, deduplicate, prioritize, and limit pool size
- **Output**: Cleaned and prioritized transaction pool
- **Data Store**: Pending transactions (memory)

**Process 2.3: Transaction Inclusion in Block**
- **Input**: Pending transactions and validator status
- **Process**: Select transactions, create block, include in block body
- **Output**: New block with included transactions
- **Data Store**: Local blockchain, transaction lifecycle (included timestamp)

**Process 2.4: Transaction Lifecycle Database Operations**
- **Input**: Transaction lifecycle events
- **Process**: Record received/included timestamps, calculate latency
- **Output**: Complete transaction lifecycle data
- **Data Store**: Transaction lifecycle table (SQLite)

**Key Transaction Processing Characteristics:**
- **Metrics as Transactions**: System metrics become blockchain transactions
- **Real-time Processing**: Continuous flow from collection to inclusion
- **Lifecycle Tracking**: Complete audit trail from receipt to inclusion
- **Pool Management**: Deduplication, prioritization, and size limits
- **Latency Measurement**: Track transaction processing time
- **MQTT + HTTP Hybrid**: MQTT for real-time, HTTP for chain sync

