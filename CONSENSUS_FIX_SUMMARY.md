# Blockchain Consensus Fix Summary

## Problems Fixed

### 1. **Race Condition in Chain Modification** ✓
**Problem**: Multiple async tasks (`_process_transactions_periodically`, `_handle_new_block`, `_resolve_forks_periodically`) were concurrently modifying `self.blocks`, causing:
- Duplicate indices: `[0, 1, 2, 4, 4, 5, ...]`
- Out-of-order indices: `[0, 1, 2, 15, 16, 13, 14, ...]`
- Missing indices: `[0, 1, 2, 4, 5, ...]` (skipping 3)

**Fix**: Added `asyncio.Lock` (`self.chain_lock`) to protect all chain read/write operations in `src/main.py`:
- Mining: Lock during pre-mining chain sync and post-mining fork resolution
- Block reception: Lock during block handling
- Periodic fork resolution: Lock entire operation

### 2. **Invalid Chain Building** ✓
**Problem**: `_build_all_chains()` in `src/consensus/pow.py` only validated hash links, not index continuity. This allowed corrupt chains like:
```
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 16, 13, 14, 15, 16, ...]
```

**Fix**: Added index continuity validation (lines 167-179):
```python
# CRITICAL: Validate index continuity (each block must be parent + 1)
for i in range(1, len(chain)):
    if chain[i].block_index != chain[i-1].block_index + 1:
        # Reject this chain
        is_valid = False
```

Now only valid chains are considered: `[0, 1, 2, 3, 4, 5, ...]`

### 3. **Hash Calculation Consistency** ✓ (Already fixed)
**Problem**: Mining hash ≠ validation hash due to inconsistent `energy_metrics` handling.

**Fix**: Store `__original_metrics__` during mining and reconstruct during validation.

## New Diagnostic Endpoint

### `/api/blocks/diagnostic`
Check blockchain health from any node:
```bash
curl http://192.168.2.106:8001/api/blocks/diagnostic | jq
```

**Output**:
```json
{
  "total_blocks": 100,
  "max_index": 99,
  "unique_indices": 100,
  "missing_indices": [],
  "missing_count": 0,
  "duplicate_indices": {},
  "invalid_relationships": [],
  "invalid_count": 0,
  "is_healthy": true  ← Should be true after fix!
}
```

## Deployment Instructions

### Step 1: Stop All Nodes
```bash
# On each Raspberry Pi
sudo systemctl stop blockchain-node
```

### Step 2: Clear Corrupt Databases
```bash
# On each node - run cleanup script
cd ~/iot-pow-blockchain
bash scripts/cleanup.sh

# Answer prompts:
# - Keep MQTT brokers? [y/N]: n
# - Remove entire repository? [y/N]: n
```

Or manually:
```bash
# On each node
sudo rm -f ~/iot-pow-blockchain/blockchain.db
sudo rm -rf ~/iot-pow-blockchain/data/
sudo rm -rf ~/iot-pow-blockchain/blockchain_data/
```

### Step 3: Deploy Fixed Code
```bash
# On each node
cd ~/iot-pow-blockchain
git pull  # Or copy updated files
```

**Modified files**:
- `src/main.py` - Added chain lock protection
- `src/consensus/pow.py` - Added index validation
- `src/monitoring/dashboard.py` - Added diagnostic endpoint

### Step 4: Restart All Nodes
```bash
# On each node
sudo systemctl start blockchain-node

# Verify it's running
sudo systemctl status blockchain-node
journalctl -u blockchain-node -f  # Watch logs
```

### Step 5: Verify Health
```bash
# Check each node's blockchain health
for port in 8001 8002 8003 8004 8005 8006; do
  echo "=== Node on port $port ==="
  curl -s http://192.168.2.106:$port/api/blocks/diagnostic | jq '.is_healthy, .total_blocks, .missing_count, .invalid_count'
done
```

**Expected output**:
```
=== Node on port 8001 ===
true
10
0
0
```

### Step 6: Monitor Consensus
```bash
# Use the verify_chain_consensus.py tool
cd ~/iot-pow-blockchain
python3 tools/verify/verify_chain_consensus.py --config config/nodes.yaml
```

**Expected output**:
```
✓ All nodes have matching chains
✓ Block hashes match at all indices
```

## What Changed

### Before (Broken)
```
Chain indices: [0, 1, 2, 4, 4, 5, 6, 12, 13, 14, 16, 17, 18, 19, 20, 22, 23, 17, ...]
                     ↑   ↑              ↑              ↑   duplicates, jumps, reversals
```

### After (Fixed)
```
Chain indices: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, ...]
                Sequential, no duplicates, no jumps
```

## Expected Behavior

1. **No more duplicate indices**: Each index appears once in the best chain
2. **Sequential indices**: `[0, 1, 2, 3, 4, 5, ...]` - no jumps or reversals
3. **Competing blocks handled correctly**: Multiple blocks at same index can exist in storage (different forks), but only the best chain is used
4. **Consensus reached**: All nodes converge to the same chain within ~10 seconds

## Troubleshooting

### If chains are still different:
```bash
# 1. Check diagnostic on each node
curl http://NODE_IP:PORT/api/blocks/diagnostic | jq

# 2. If not healthy, clear database again
sudo systemctl stop blockchain-node
sudo rm -rf ~/iot-pow-blockchain/blockchain.db ~/iot-pow-blockchain/data/
sudo systemctl start blockchain-node

# 3. Verify genesis block matches
curl http://NODE_IP:PORT/api/blocks?start_index=0&end_index=0 | jq '.[0].hash'
# Should be IDENTICAL on all nodes
```

### Check for race condition logs:
```bash
journalctl -u blockchain-node -f | grep "FORK RESOLUTION\|PROCESS TX\|Better chain"
```

### Monitor block creation:
```bash
journalctl -u blockchain-node -f | grep "New block created\|Block mined"
```

## Testing After Deployment

Run the test plan:
```bash
cd ~/iot-pow-blockchain/tools
bash run_test_plan.sh --config config/nodes.yaml --duration 300
```

Then check consensus:
```bash
python3 verify/verify_chain_consensus.py --config ../config/nodes.yaml
```

## Files Modified

1. **src/main.py**
   - Added `self.chain_lock = asyncio.Lock()`
   - Protected `_process_transactions_periodically` (lines 706-823)
   - Protected `_resolve_forks_periodically` (lines 867-912)

2. **src/consensus/pow.py**
   - Added index validation in `_build_all_chains` (lines 167-179)
   - Rejects chains with non-sequential indices

3. **src/monitoring/dashboard.py**
   - Added `/api/blocks/diagnostic` endpoint (lines 320-375)
   - Identifies missing indices, duplicates, and invalid relationships

## Prevention

These fixes prevent future corruption by:
1. **Atomic operations**: Chain reads/writes are protected by locks
2. **Validation**: Invalid chains are rejected during fork resolution
3. **Monitoring**: Diagnostic endpoint detects corruption early

