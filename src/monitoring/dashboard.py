from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import time
from typing import Dict, Any, Optional, List
from monitoring.metrics import BlockchainMetrics

app = FastAPI(title="PoW Blockchain Dashboard", version="1.0.0")

# Global metrics instance
metrics: Optional[BlockchainMetrics] = None

def set_metrics_instance(metrics_instance: BlockchainMetrics):
    """Set the global metrics instance."""
    global metrics
    metrics = metrics_instance

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PoW Blockchain Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .metric-card {
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-radius: 10px;
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
        }
        .card-title {
            color: #2c3e50;
            font-weight: bold;
        }
        .card-text {
            font-size: 1.2em;
            color: #34495e;
        }
        .node-card {
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
        }
        .node-list-container {
            max-height: 300px;
            overflow-y: auto;
        }
        .refresh-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-online { background-color: #27ae60; }
        .status-offline { background-color: #e74c3c; }
    </style>
</head>
<body>
    <div class="container-fluid mt-4">
        <h1 class="text-center mb-4">PoW Blockchain Dashboard</h1>
        
        <button class="btn btn-primary refresh-btn" onclick="refreshData()">
            <i class="bi bi-arrow-clockwise"></i> Refresh
        </button>

        <div class="row">
            <div class="col-md-6">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Consensus Protocol</h5>
                        <p class="card-text" id="consensus-protocol">Proof of Work</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Overall Power Usage</h5>
                        <p class="card-text" id="overall-power-usage">Loading...</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-4">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Block Count</h5>
                        <p class="card-text" id="block-count">Loading...</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Blockchain Size</h5>
                        <p class="card-text" id="blockchain-size">Loading...</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Transaction Throughput</h5>
                        <p class="card-text" id="tps">Loading...</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Current Difficulty</h5>
                        <p class="card-text" id="current-difficulty">Loading...</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Chain Work</h5>
                        <p class="card-text" id="chain-work">Loading...</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Orphan Blocks</h5>
                        <p class="card-text" id="orphan-blocks">Loading...</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-12">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Network Nodes and Hash Rates</h5>
                        <div class="node-list-container" id="miners-list">
                            <!-- Miners will be rendered here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-12">
                <div class="card metric-card">
                    <div class="card-body">
                        <h5 class="card-title">Individual Node Metrics</h5>
                        <div id="node-metrics">
                            <!-- Individual node cards will be rendered here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        async function refreshData() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Error fetching metrics:', error);
            }
        }

        function updateDashboard(data) {
            // Update basic metrics
            document.getElementById('consensus-protocol').textContent = data.consensus_protocol || 'Proof of Work';
            // Format power usage with appropriate units
            const totalPower = data.power_metrics.total_power;
            let powerText;
            if (totalPower >= 1000000) {
                powerText = `Cumulative Mining: ${(totalPower / 1000000).toFixed(2)}MW`;
            } else if (totalPower >= 1000) {
                powerText = `Cumulative Mining: ${(totalPower / 1000).toFixed(2)}kW`;
            } else {
                powerText = `Cumulative Mining: ${totalPower.toFixed(2)}W`;
            }
            document.getElementById('overall-power-usage').textContent = powerText;
            document.getElementById('block-count').textContent = data.blockchain_metrics.total_blocks;
            document.getElementById('blockchain-size').textContent = 
                `${(data.blockchain_size / (1024 * 1024)).toFixed(2)} MB`; // Convert bytes to MB
            document.getElementById('current-difficulty').textContent = data.current_difficulty || 'N/A';
            document.getElementById('chain-work').textContent = data.chain_work || 'N/A';
            document.getElementById('orphan-blocks').textContent = data.orphan_blocks_count || '0';

            // Update Network Nodes List
            const minersList = document.getElementById('miners-list');
            minersList.innerHTML = ''; // Clear previous
            const sortedNodes = Object.entries(data.all_miners_metrics || {})
                                        .sort(([, hashRateA], [, hashRateB]) => hashRateB - hashRateA);
            if (sortedNodes.length > 0) {
                sortedNodes.forEach(([nodeId, hashRate]) => {
                    const p = document.createElement('p');
                    p.textContent = `${nodeId}: ${hashRate.toFixed(0)} H/s`;
                    minersList.appendChild(p);
                });
            } else {
                minersList.textContent = 'No network nodes found.';
            }

            // Update Individual Node Metrics
            const nodeMetricsContainer = document.getElementById('node-metrics');
            nodeMetricsContainer.innerHTML = ''; // Clear previous

            Object.entries(data.system_metrics).forEach(([nodeId, nodeData]) => {
                const nodeCard = document.createElement('div');
                nodeCard.className = 'col-md-4 mb-3';
                nodeCard.innerHTML = `
                    <div class="card node-card">
                        <div class="card-body">
                            <h6 class="card-title">
                                <span class="status-indicator ${nodeData.timestamp > Date.now() / 1000 - 60 ? 'status-online' : 'status-offline'}"></span>
                                ${nodeId}
                            </h6>
                            <p class="card-text">CPU: ${nodeData.cpu_percent.toFixed(1)}%</p>
                            <p class="card-text">Mem: ${nodeData.memory_percent.toFixed(1)}%</p>
                            <p class="card-text">Temp: ${nodeData.temperature.toFixed(1)}°C</p>
                            <p class="card-text">Power: ${nodeData.power_usage.toFixed(2)}W</p>
                            <p class="card-text">Blocks: ${nodeData.block_count}</p>
                            <p class="card-text">Pending TXs: ${nodeData.pending_transactions}</p>
                            <p class="card-text">Hash Rate: ${data.all_miners_metrics[nodeId] || 0} H/s</p>
                            <p class="card-text">Mining: ${data.system_metrics[nodeId].is_mining ? 'Yes' : 'No'}</p>
                        </div>
                    </div>
                `;
                nodeMetricsContainer.appendChild(nodeCard);
            });

            // Update TPS
            document.getElementById('tps').textContent = `${data.blockchain_metrics.tps.toFixed(2)} TPS`;
        }

        // Auto-refresh every 5 seconds
        setInterval(refreshData, 5000);

        // Initial load
        refreshData();
    </script>
</body>
</html>
    """

@app.get("/api/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get all aggregated metrics from BlockchainMetrics."""
    # Ensure metrics instance is set before trying to use it
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    
    # Get all the metrics
    system_metrics = metrics.get_system_metrics()
    power_metrics = metrics.get_power_metrics()
    blockchain_metrics = metrics.get_blockchain_metrics()
    
    # Debug logging
    print(f"[DASHBOARD DEBUG] System metrics keys: {list(system_metrics.keys())}")
    for node_id, node_data in system_metrics.items():
        print(f"[DASHBOARD DEBUG] {node_id}: block_count={node_data.get('block_count', 'MISSING')}, pending_transactions={node_data.get('pending_transactions', 'MISSING')}")
    
    return {
        "consensus_protocol": "Proof of Work",
        "power_metrics": power_metrics,
        "blockchain_metrics": {
            **blockchain_metrics,
            # "total_blocks": 0 # Placeholder for now, to be fetched from storage
        },
        "system_metrics": system_metrics, # This now returns all nodes' metrics
        "all_miners_metrics": metrics.get_all_miners_metrics(),
        "current_difficulty": metrics.get_current_difficulty(),
        "blockchain_size": metrics.get_blockchain_size(),
        "chain_work": metrics.get_chain_work(),
        "orphan_blocks_count": metrics.get_orphan_blocks_count()
    }

@app.get("/api/blocks")
async def get_blocks(start_index: int = 0, end_index: int = -1) -> List[Dict[str, Any]]:
    """Get blocks from the blockchain."""
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    
    try:
        blocks = metrics.get_blocks_from_storage(start_index, end_index)
        return [block.to_dict() for block in blocks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving blocks: {str(e)}")

@app.get("/api/consensus-protocol")
async def get_consensus_protocol() -> Dict[str, str]:
    """Get consensus protocol information."""
    return {"protocol": "Proof of Work"}

@app.get("/api/blockchain-metrics")
async def get_blockchain_metrics() -> Dict[str, Any]:
    """Get blockchain-specific metrics."""
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    
    return metrics.get_blockchain_metrics()

@app.get("/api/system-metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics for all nodes."""
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    
    return metrics.get_system_metrics()

@app.get("/api/energy")
async def get_energy() -> Dict[str, Any]:
    """Get energy consumption data for this node."""
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    
    cumulative_energy = metrics.get_cumulative_mining_power()
    
    return {
        "cumulative_energy": cumulative_energy,
        "node_id": metrics.local_node_id,
        "timestamp": time.time()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 