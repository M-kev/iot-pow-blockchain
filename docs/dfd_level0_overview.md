# Level 0 DFD - IoT DPoS Blockchain System Overview

## Context Diagram (Level 0 DFD)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    LEVEL 0 DFD - CONTEXT DIAGRAM                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────────┐
                                    │   MQTT Broker 1 │
                                    │   192.168.2.10  │
                                    │   (Primary)     │
                                    └─────────┬───────┘
                                              │
                                              │ MQTT Messages
                                              │ (Metrics, Blocks, TXs)
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    │                         │                         │
        ┌───────────▼──────────┐    ┌─────────▼─────────┐    ┌───────────▼──────────┐
        │   Raspberry Pi 1     │    │   Raspberry Pi 2  │    │   Raspberry Pi 3     │
        │   pi_node_1          │    │   pi_node_2       │    │   pi_node_3          │
        │   (Node 1)           │    │   (Node 2)        │    │   (Node 3)           │
        └───────────┬──────────┘    └─────────┬─────────┘    └───────────┬──────────┘
                    │                         │                         │
                    │                         │                         │
        ┌───────────▼──────────┐    ┌─────────▼─────────┐    ┌───────────▼──────────┐
        │   Raspberry Pi 4     │    │   Raspberry Pi 5  │    │   Raspberry Pi 6     │
        │   pi_node_4          │    │   pi_node_5       │    │   pi_node_6          │
        │   (Node 4)           │    │   (Node 5)        │    │   (Node 6)           │
        └───────────┬──────────┘    └─────────┬─────────┘    └───────────┬──────────┘
                    │                         │                         │
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              │
                                              │ HTTP Chain Sync
                                              │
                                    ┌─────────▼─────────┐
                                    │   MQTT Broker 2   │
                                    │   192.168.2.11    │
                                    │   (Backup)        │
                                    └───────────────────┘

External Entities:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   System        │    │   Network       │    │   User          │    │   Energy        │
│   Monitor       │    │   Environment   │    │   Dashboard     │    │   Sensors       │
│   (psutil)      │    │   (tc/netem)    │    │   (Browser)     │    │   (CPU, Temp)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

Data Stores:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SQLite        │    │   Environment   │    │   Systemd       │    │   MQTT          │
│   Database      │    │   Variables     │    │   Service       │    │   Topics        │
│   (blockchain.db│    │   (.env)        │    │   Files         │    │   (pub/sub)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

Key Data Flows:
1. System Metrics → Node → MQTT Broker → All Nodes
2. Incoming Metrics → Transaction Pool → Block Creation → Chain Storage
3. Node → HTTP Client → Peer Nodes (Chain Sync)
4. SQLite → FastAPI → User Dashboard
5. Energy Sensors → Energy Monitor → Metrics Collection
```

