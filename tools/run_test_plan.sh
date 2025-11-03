#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CFG=$ROOT/tools/config/nodes.yaml
STAMP=$(date +%Y%m%d-%H%M%S)
ART=$ROOT/artifacts/$STAMP
mkdir -p "$ART/raw" "$ART/merged" "$ART/charts"

PROFILE=${1:-baseline}     # baseline|moderate|harsh|clear
DURATION=${2:-300}         # seconds
RATE=${3:-20}              # msgs/sec per publisher
NODES=${4:-10}             # simulated publishers

echo "[Orchestrator] Using profile=$PROFILE duration=$DURATION rate=$RATE nodes=$NODES"

# 1) Apply network profile
$ROOT/tools/netem/netem.sh eth0 "$PROFILE"

# 2) Start load
# Parse YAML config using Python (more reliable than yq)
read HOST PORT USER PASS MTOP TTOP <<< $(python3 <<PYEOF
import yaml
import sys
try:
    with open("$CFG", 'r') as f:
        cfg = yaml.safe_load(f)
    mqtt = cfg.get('mqtt', {})
    topics = cfg.get('topics', {})
    host = mqtt.get('host', '')
    port = mqtt.get('port', 1883)
    user = mqtt.get('username', '')
    passwd = mqtt.get('password', '')
    mtop = topics.get('metrics', 'metrics')
    ttop = topics.get('transactions', 'transactions')
    print(f"{host} {port} {user} {passwd} {mtop} {ttop}")
except Exception as e:
    print(f"ERROR loading config: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
)

if [ -z "$HOST" ]; then
    echo "ERROR: Failed to read MQTT broker configuration from $CFG" >&2
    exit 1
fi

echo "[Orchestrator] MQTT Broker: $HOST:$PORT"
python3 "$ROOT/tools/load/mqtt_load.py" --host "$HOST" --port "$PORT" \
  --username "$USER" --password "$PASS" \
  --metrics_topic "$MTOP" --tx_topic "$TTOP" \
  --nodes "$NODES" --rate "$RATE" --duration "$DURATION"

# 3) Collect CSVs
python3 "$ROOT/tools/collect/pull_csvs.py" --config "$CFG" --out "$ART/raw"

# 4) Merge + report
python3 "$ROOT/tools/report/generate_report.py" --in "$ART/raw" --out "$ART"

# 5) Clear network shaping
$ROOT/tools/netem/netem.sh eth0 clear

echo "Artifacts written to: $ART"


