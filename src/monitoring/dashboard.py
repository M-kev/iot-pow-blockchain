from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import time
from typing import Dict, Any, Optional, List
import csv
import io
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

@app.get("/api/blocks/headers")
async def get_block_headers(start_index: int = 0, end_index: int = -1) -> List[Dict[str, Any]]:
    """
    Get lightweight block headers for header-first sync.
    
    Headers contain only essential information for chain verification:
    - Block index, hash, previous_hash
    - Proof of Work (difficulty, nonce)
    - Timestamp and miner
    
    This endpoint is significantly faster than /api/blocks because:
    - No transaction data (saves ~90% bandwidth)
    - No detailed energy metrics
    - Typical header: ~200 bytes vs full block: ~1-10KB
    
    Use case: Initial sync for nodes that are far behind
    """
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")

    try:
        from ..consensus.block_header import BlockHeader
        
        # Get full blocks from storage
    blocks = metrics.get_blocks_from_storage(start_index, end_index)
        
        # Convert to lightweight headers
        headers = [BlockHeader.from_block(block).to_dict() for block in blocks]
        
        return headers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving headers: {str(e)}")

@app.get("/api/blocks/diagnostic")
async def get_blocks_diagnostic():
    """Diagnostic endpoint to identify corrupt blocks and missing indices."""
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    
    try:
        all_blocks = metrics.get_blocks_from_storage(0, -1)
        
        # Group blocks by index
        blocks_by_index = {}
        for block in all_blocks:
            idx = block.block_index
            if idx not in blocks_by_index:
                blocks_by_index[idx] = []
            blocks_by_index[idx].append(block)
        
        # Find missing indices
        if blocks_by_index:
            max_index = max(blocks_by_index.keys())
            missing_indices = [i for i in range(max_index + 1) if i not in blocks_by_index]
        else:
            max_index = -1
            missing_indices = []
        
        # Find duplicate indices
        duplicate_indices = {idx: len(blocks) for idx, blocks in blocks_by_index.items() if len(blocks) > 1}
        
        # Validate parent-child relationships
        invalid_relationships = []
        for block in all_blocks:
            if block.block_index > 0:
                # Find parent
                parent = next((b for b in all_blocks if b.hash == block.previous_hash), None)
                if parent:
                    if block.block_index != parent.block_index + 1:
                        invalid_relationships.append({
                            "block_index": block.block_index,
                            "block_hash": block.hash[:16] + "...",
                            "parent_index": parent.block_index,
                            "expected_index": parent.block_index + 1
                        })
        
        return {
            "total_blocks": len(all_blocks),
            "max_index": max_index,
            "unique_indices": len(blocks_by_index),
            "missing_indices": missing_indices[:20],  # First 20
            "missing_count": len(missing_indices),
            "duplicate_indices": duplicate_indices,
            "invalid_relationships": invalid_relationships[:20],  # First 20
            "invalid_count": len(invalid_relationships),
            "is_healthy": len(missing_indices) == 0 and len(duplicate_indices) == 0 and len(invalid_relationships) == 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in diagnostic: {str(e)}")

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

@app.get("/api/export/block-metrics.csv")
async def export_block_metrics_csv():
    """Export block metrics as CSV."""
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    
    try:
        # Get block metrics from storage
        block_metrics = metrics.storage.export_block_metrics()
        
        if not block_metrics:
            # Return empty CSV with headers
            csv_content = "block_index,created_timestamp,block_interval,consensus_time,power_usage\n"
        else:
            # Convert to CSV
            csv_content = "block_index,created_timestamp,block_interval,consensus_time,power_usage\n"
            for metric in block_metrics:
                csv_content += f"{metric['block_index']},{metric['created_timestamp']},{metric['block_interval']},{metric['consensus_time']},{metric['power_usage']}\n"
        
        from fastapi.responses import Response
        return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=block-metrics.csv"})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting block metrics: {str(e)}")

@app.get("/api/export/transaction-lifecycle.csv")
async def export_transaction_lifecycle_csv():
    """Export transaction lifecycle as CSV."""
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    
    try:
        # Get transaction lifecycle from storage
        tx_lifecycle = metrics.storage.export_transaction_lifecycle()
        
        if not tx_lifecycle:
            # Return empty CSV with headers
            csv_content = "tx_hash,received_timestamp,included_timestamp,block_index\n"
        else:
            # Convert to CSV
            csv_content = "tx_hash,received_timestamp,included_timestamp,block_index\n"
            for tx in tx_lifecycle:
                # Handle None values for pending transactions
                included_ts = tx['included_timestamp'] if tx['included_timestamp'] is not None else ""
                block_idx = tx['block_index'] if tx['block_index'] is not None else ""
                csv_content += f"{tx['tx_hash']},{tx['received_timestamp']},{included_ts},{block_idx}\n"
        
        from fastapi.responses import Response
        return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=transaction-lifecycle.csv"})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting transaction lifecycle: {str(e)}")

@app.get("/api/resource-metrics")
async def get_resource_metrics():
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    try:
        return metrics.get_resource_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting resource metrics: {str(e)}")

@app.get("/api/operation-metrics")
async def get_operation_metrics(operation_type: Optional[str] = None):
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    try:
        return metrics.get_operation_metrics(operation_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting operation metrics: {str(e)}")

@app.get("/api/export/resource-metrics.csv")
async def export_resource_metrics_csv():
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    fieldnames = [
        "operation_id","operation_type","start_time","end_time","duration",
        "cpu_initial","cpu_final","cpu_avg",
        "memory_initial_mb","memory_final_mb","memory_delta_mb",
        "network_bytes_sent","network_bytes_recv","network_packets_sent","network_packets_recv"
    ]
    try:
        # Use unlimited operation_metrics lists for block_* operations instead of limited deque
        # This ensures we get all validation and creation metrics, not just recent ones
        op_metrics = metrics.get_operation_metrics()
        block_validation = op_metrics.get('block_validation', [])
        block_creation = op_metrics.get('block_creation', [])
        # Combine all block_* operations from unlimited lists
        data = block_validation + block_creation
        def generate():
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            if data:
                for r in data:
                    row = {
                        'operation_id': r.get('operation_id'),
                        'operation_type': r.get('operation_type'),
                        'start_time': r.get('start_time'),
                        'end_time': r.get('end_time'),
                        'duration': r.get('duration'),
                        'cpu_initial': r.get('cpu_usage', {}).get('initial'),
                        'cpu_final': r.get('cpu_usage', {}).get('final'),
                        'cpu_avg': r.get('cpu_usage', {}).get('avg'),
                        'memory_initial_mb': r.get('memory_usage', {}).get('initial_mb'),
                        'memory_final_mb': r.get('memory_usage', {}).get('final_mb'),
                        'memory_delta_mb': r.get('memory_usage', {}).get('memory_delta_mb'),
                        'network_bytes_sent': r.get('network_usage', {}).get('bytes_sent'),
                        'network_bytes_recv': r.get('network_usage', {}).get('bytes_recv'),
                        'network_packets_sent': r.get('network_usage', {}).get('packets_sent'),
                        'network_packets_recv': r.get('network_usage', {}).get('packets_recv'),
                    }
                    writer.writerow(row)
            yield buf.getvalue()
        return StreamingResponse(generate(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=resource-metrics.csv"})
    except Exception as e:
        # Always return CSV even on error (headers only)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        return StreamingResponse(io.StringIO(buf.getvalue()), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=resource-metrics.csv"})

@app.get("/api/export/operation-metrics.csv")
async def export_operation_metrics_csv(operation_type: Optional[str] = None):
    if metrics is None:
        raise HTTPException(status_code=500, detail="Metrics instance not initialized.")
    try:
        ops = metrics.get_operation_metrics(operation_type)
        rows: List[Dict[str, Any]] = []
        # Normalize to iterable of (type, list)
        if operation_type:
            ops_items = [(operation_type, ops if isinstance(ops, list) else [])]
        else:
            ops_items = list(ops.items()) if isinstance(ops, dict) else []

        # Determine fieldnames per type
        def fieldnames_for(op_type: str) -> List[str]:
            if op_type == 'network_operations':
                return ["operation","timestamp","bytes_transferred","duration","success","throughput_mbps","operation_type"]
            if op_type == 'database_operations':
                return ["operation","timestamp","duration","rows_affected","throughput_rows_per_sec","operation_type"]
            # block_* types
            return [
                "operation_id","operation_type","start_time","end_time","duration",
                "cpu_initial","cpu_final","cpu_avg",
                "memory_initial_mb","memory_final_mb","memory_delta_mb",
                "network_bytes_sent","network_bytes_recv","network_packets_sent","network_packets_recv"
            ]

        # If specific type, write only that schema; else write mixed schema with operation_type appended
        buf = io.StringIO()
        if operation_type:
            fn = fieldnames_for(operation_type)
            writer = csv.DictWriter(buf, fieldnames=fn, extrasaction='ignore')
            writer.writeheader()
            for _, items in ops_items:
                for r in items:
                    row = dict(r)
                    if operation_type.startswith('block_'):
                        row = {
                            'operation_id': r.get('operation_id'),
                            'operation_type': r.get('operation_type'),
                            'start_time': r.get('start_time'),
                            'end_time': r.get('end_time'),
                            'duration': r.get('duration'),
                            'cpu_initial': r.get('cpu_usage', {}).get('initial'),
                            'cpu_final': r.get('cpu_usage', {}).get('final'),
                            'cpu_avg': r.get('cpu_usage', {}).get('avg'),
                            'memory_initial_mb': r.get('memory_usage', {}).get('initial_mb'),
                            'memory_final_mb': r.get('memory_usage', {}).get('final_mb'),
                            'memory_delta_mb': r.get('memory_usage', {}).get('memory_delta_mb'),
                            'network_bytes_sent': r.get('network_usage', {}).get('bytes_sent'),
                            'network_bytes_recv': r.get('network_usage', {}).get('bytes_recv'),
                            'network_packets_sent': r.get('network_usage', {}).get('packets_sent'),
                            'network_packets_recv': r.get('network_usage', {}).get('packets_recv'),
                        }
                    else:
                        row['operation_type'] = operation_type
                    writer.writerow(row)
        else:
            # Mixed export; union schema is complicated, so export per row with operation_type
            # We'll use the block_* schema where applicable, otherwise the specific schema and include operation_type
            # Start with header for the superset of known fields
            superset_fields = [
                "operation_id","operation_type","start_time","end_time","duration",
                "cpu_initial","cpu_final","cpu_avg",
                "memory_initial_mb","memory_final_mb","memory_delta_mb",
                "network_bytes_sent","network_bytes_recv","network_packets_sent","network_packets_recv",
                "operation","timestamp","bytes_transferred","success","throughput_mbps","rows_affected","throughput_rows_per_sec"
            ]
            writer = csv.DictWriter(buf, fieldnames=superset_fields, extrasaction='ignore')
            writer.writeheader()
            for op_type, items in ops_items:
                for r in items:
                    if op_type.startswith('block_'):
                        row = {
                            'operation_id': r.get('operation_id'),
                            'operation_type': r.get('operation_type'),
                            'start_time': r.get('start_time'),
                            'end_time': r.get('end_time'),
                            'duration': r.get('duration'),
                            'cpu_initial': r.get('cpu_usage', {}).get('initial'),
                            'cpu_final': r.get('cpu_usage', {}).get('final'),
                            'cpu_avg': r.get('cpu_usage', {}).get('avg'),
                            'memory_initial_mb': r.get('memory_usage', {}).get('initial_mb'),
                            'memory_final_mb': r.get('memory_usage', {}).get('final_mb'),
                            'memory_delta_mb': r.get('memory_usage', {}).get('memory_delta_mb'),
                            'network_bytes_sent': r.get('network_usage', {}).get('bytes_sent'),
                            'network_bytes_recv': r.get('network_usage', {}).get('bytes_recv'),
                            'network_packets_sent': r.get('network_usage', {}).get('packets_sent'),
                            'network_packets_recv': r.get('network_usage', {}).get('packets_recv'),
                        }
                    elif op_type == 'network_operations':
                        row = {
                            **r,
                            'operation_type': op_type
                        }
                    elif op_type == 'database_operations':
                        row = {
                            **r,
                            'operation_type': op_type
                        }
                    else:
                        row = {**r, 'operation_type': op_type}
                    writer.writerow(row)
        return StreamingResponse(io.StringIO(buf.getvalue()), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=operation-metrics.csv"})
    except Exception as e:
        # On error, still return CSV headers
        if operation_type in ('network_operations', 'database_operations'):
            fn = ["operation","timestamp","bytes_transferred","duration","success","throughput_mbps"] if operation_type == 'network_operations' else ["operation","timestamp","duration","rows_affected","throughput_rows_per_sec"]
        else:
            fn = [
                "operation_id","operation_type","start_time","end_time","duration",
                "cpu_initial","cpu_final","cpu_avg",
                "memory_initial_mb","memory_final_mb","memory_delta_mb",
                "network_bytes_sent","network_bytes_recv","network_packets_sent","network_packets_recv"
            ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fn, extrasaction='ignore')
    writer.writeheader()
        return StreamingResponse(io.StringIO(buf.getvalue()), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=operation-metrics.csv"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 