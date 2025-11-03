import argparse, os, requests, yaml, sys


def fetch(url: str) -> str:
    """Fetch URL with error handling."""
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.text
    except requests.exceptions.RequestException as e:
        print(f"  ERROR: Failed to fetch {url}: {e}", file=sys.stderr)
        return ""  # Return empty string on error


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    
    # Load and validate config
    if not os.path.exists(a.config):
        print(f"ERROR: Config file not found: {a.config}", file=sys.stderr)
        sys.exit(1)
    
    with open(a.config, "r") as f:
        cfg = yaml.safe_load(f)
    
    if "nodes" not in cfg:
        print("ERROR: No 'nodes' section in config file", file=sys.stderr)
        sys.exit(1)
    
    print(f"Collecting CSVs from {len(cfg['nodes'])} nodes...")
    
    # CSV endpoints to collect
    csv_endpoints = [
        ("block-metrics.csv", "block-metrics.csv"),
        ("transaction-lifecycle.csv", "tx-lifecycle.csv"),
        ("resource-metrics.csv", "resource-metrics.csv"),
        ("operation-metrics.csv", "operation-metrics.csv"),
    ]
    
    success_count = 0
    error_count = 0
    
    for n in cfg["nodes"]:
        node_id = n.get('id', 'unknown')
        node_ip = n.get('ip')
        node_port = n.get('dashboard_port')
        
        if not all([node_id, node_ip, node_port]):
            print(f"  WARNING: Skipping incomplete node config: {n}", file=sys.stderr)
            error_count += 1
            continue
        
        base_url = f"http://{node_ip}:{node_port}/api/export"
        print(f"  Fetching from {node_id} ({node_ip}:{node_port})...")
        
        for endpoint, filename in csv_endpoints:
            url = f"{base_url}/{endpoint}"
            content = fetch(url)
            
            if content:
                out_path = os.path.join(a.out, f"{node_id}-{filename}")
                with open(out_path, "w") as f:
                    f.write(content)
                print(f"    ✓ {filename}")
                success_count += 1
            else:
                print(f"    ✗ {filename} (empty or failed)")
                error_count += 1
    
    print(f"\nCSV collection complete. Success: {success_count}, Errors: {error_count}")
    
    if error_count > 0 and success_count == 0:
        print("\nERROR: All CSV endpoints failed. Check node connectivity.", file=sys.stderr)
        sys.exit(1)
    elif error_count > 0:
        print("\nWARNING: Some CSV endpoints failed. This may be normal if endpoints are not available.", file=sys.stderr)


