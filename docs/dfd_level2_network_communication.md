# Level 2 DFD - Network Communication Flow

## Level 2 DFD - Detailed Network Communication

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    LEVEL 2 DFD - NETWORK COMMUNICATION                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

External Entities:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MQTT          │    │   HTTP          │    │   Network       │    │   System        │
│   Broker 1      │    │   Peers         │    │   Environment   │    │   Clock         │
│   (192.168.2.10)│    │   (Nodes)       │    │   (tc/netem)    │    │   (Time)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

Data Stores:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MQTT          │    │   HTTP          │    │   Network       │    │   Connection    │
│   Client        │    │   Client        │    │   Config        │    │   State         │
│   (paho-mqtt)   │    │   (httpx)       │    │   (network_     │    │   (Memory)      │
│                 │    │                 │    │   config.py)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

Detailed Processes:

1. MQTT CONNECTION MANAGEMENT
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  1.1 MQTT Broker Connection and Failover                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Initialize    │───▶│   Try Primary   │───▶│   Check         │───▶│   Success?      │      │
│  │   MQTT Client   │    │   Broker        │    │   Connection    │    │   (Connected)   │      │
│  │   (paho-mqtt)   │    │   (192.168.2.10)│    │   Status        │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Try Backup    │───▶│   Update        │───▶│   Subscribe to  │───▶│   Start          │      │
│  │   Broker        │    │   Active        │    │   Topics        │    │   Message        │      │
│  │   (192.168.2.11)│    │   Broker Index  │    │   (iot/metrics, │    │   Processing     │      │
│  │                 │    │   (active_      │    │   iot/blocks)   │    │   (Loop)         │      │
│  │                 │    │   broker_index) │    │                 │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

2. MQTT MESSAGE PUBLISHING
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  1.2 MQTT Message Publishing with Retry Logic                                                    │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Prepare       │───▶│   Check         │───▶│   Publish       │───▶│   Handle         │      │
│  │   Message       │    │   Connection    │    │   Message       │    │   Publish        │      │
│  │   (JSON)        │    │   Status        │    │   (publish)     │    │   Result         │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Retry on      │───▶│   Switch        │───▶│   Log           │───▶│   Continue       │      │
│  │   Failure       │    │   Broker        │    │   Success/      │    │   (Next         │      │
│  │   (3 attempts)  │    │   (Failover)    │    │   Error         │    │   Message)       │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

3. MQTT MESSAGE RECEPTION
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  1.3 MQTT Message Reception and Processing                                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Receive       │───▶│   Parse         │───▶│   Route by      │───▶│   Process        │      │
│  │   Message       │    │   JSON          │    │   Topic         │    │   Message        │      │
│  │   (on_message)  │    │   (json.loads)  │    │   (iot/metrics  │    │   (Type-         │      │
│  │                 │    │                 │    │   vs iot/blocks)│    │   specific)      │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Validate      │───▶│   Update        │───▶│   Log           │───▶│   Continue       │      │
│  │   Message       │    │   Metrics       │    │   Reception     │    │   (Next         │      │
│  │   (Structure)   │    │   (Real-time)   │    │   (Debug)       │    │   Message)       │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

4. HTTP CHAIN SYNCHRONIZATION
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  2.1 HTTP Peer Discovery and Chain Request                                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Get Peer      │───▶│   Build HTTP    │───▶│   Send GET      │───▶│   Handle         │      │
│  │   List          │    │   URL           │    │   Request       │    │   Response       │      │
│  │   (Config)      │    │   (http://ip:   │    │   (httpx.get)   │    │   (Status)       │      │
│  │                 │    │   port/chain)   │    │                 │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Parse JSON    │───▶│   Validate      │───▶│   Compare       │───▶│   Update         │      │
│  │   Response      │    │   Chain         │    │   Chain         │    │   Local Chain    │      │
│  │   (json.loads)  │    │   Structure     │    │   Lengths       │    │   (If Longer)    │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

5. HTTP RESPONSE HANDLING
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  2.2 HTTP Response Processing and Error Handling                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Check HTTP    │───▶│   Handle        │───▶│   Parse         │───▶│   Validate       │      │
│  │   Status Code   │    │   Timeout       │    │   Response      │    │   Data           │      │
│  │   (200, 404,    │    │   (30s limit)   │    │   (JSON)        │    │   (Structure)    │      │
│  │   500, etc.)    │    │                 │    │                 │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Log Error     │───▶│   Retry         │───▶│   Update        │───▶│   Continue       │      │
│  │   (Debug)       │    │   (Next Peer)   │    │   Sync Metrics  │    │   (Next Sync)    │      │
│  │                 │    │                 │    │   (Sync Time)   │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

6. NETWORK ERROR HANDLING
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│  3.1 Network Error Detection and Recovery                                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Monitor       │───▶│   Detect        │───▶│   Classify      │───▶│   Apply          │      │
│  │   Connection    │    │   Network       │    │   Error Type    │    │   Recovery       │      │
│  │   Health        │    │   Issues        │    │   (Timeout,     │    │   Strategy       │      │
│  │                 │    │                 │    │   Connection,   │    │                 │      │
│  │                 │    │                 │    │   Auth)         │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │                       │              │
│           └───────────────────────┼───────────────────────┼───────────────────────┘              │
│                                   │                       │                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   Switch        │───▶│   Retry         │───▶│   Log           │───▶│   Update         │      │
│  │   Broker/Peer   │    │   Connection    │    │   Recovery      │    │   Connection     │      │
│  │   (Failover)    │    │   (Exponential  │    │   (Debug)       │    │   State          │      │
│  │                 │    │   Backoff)      │    │                 │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

Data Flows:
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   MQTT          │   HTTP          │   Network       │   Connection    │   Error         │
│   Messages      │   Requests      │   Config        │   State         │   Events        │
│   (JSON)        │   (GET/POST)    │   (Brokers,     │   (Connected,   │   (Timeout,     │
│                 │                 │   Peers, Auth)  │   Disconnected, │   Connection,   │
│                 │                 │                 │   Reconnecting) │   Auth)          │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

## Level 2 DFD - Network Communication Details

**Process 1.1: MQTT Broker Connection and Failover**
- **Input**: Network configuration and broker list
- **Process**: Try primary broker, failover to backup on connection failure
- **Output**: Active MQTT connection with subscribed topics
- **Data Store**: Connection state (memory)

**Process 1.2: MQTT Message Publishing with Retry Logic**
- **Input**: Prepared JSON messages
- **Process**: Check connection, publish with retry on failure
- **Output**: Published messages or error status
- **Data Store**: None (network transmission)

**Process 1.3: MQTT Message Reception and Processing**
- **Input**: MQTT messages from broker
- **Process**: Parse JSON, route by topic, validate structure
- **Output**: Processed messages for metrics or blocks
- **Data Store**: Real-time metrics (memory)

**Process 2.1: HTTP Peer Discovery and Chain Request**
- **Input**: Peer list from configuration
- **Process**: Build HTTP URLs, send GET requests for chain data
- **Output**: Chain data from peers
- **Data Store**: HTTP client state (memory)

**Process 2.2: HTTP Response Processing and Error Handling**
- **Input**: HTTP responses from peers
- **Process**: Check status codes, handle timeouts, parse JSON
- **Output**: Validated chain data or error status
- **Data Store**: Sync metrics (SQLite)

**Process 3.1: Network Error Detection and Recovery**
- **Input**: Connection health monitoring
- **Process**: Detect issues, classify errors, apply recovery strategies
- **Output**: Recovered connections or error logs
- **Data Store**: Connection state (memory)

**Key Network Communication Characteristics:**
- **Dual MQTT Brokers**: Primary and backup with automatic failover
- **HTTP Chain Sync**: Peer-to-peer chain synchronization
- **Retry Logic**: Exponential backoff for failed connections
- **Error Classification**: Timeout, connection, authentication errors
- **Real-time Monitoring**: Continuous connection health checks
- **Graceful Degradation**: System continues with reduced functionality on network issues

