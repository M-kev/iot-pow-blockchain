#!/usr/bin/env python3
"""
Verify that all nodes have the same blockchain (consensus verification).
Compares chain length, latest block hash, and all block hashes across all nodes.
"""

import argparse
import sys
import requests
from typing import Dict, List, Optional, Tuple
import yaml
from pathlib import Path


def load_config(config_path: str) -> Dict:
    """Load node configuration from YAML."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def fetch_chain_info(node_ip: str, port: int, timeout: int = 5) -> Optional[Dict]:
    """Fetch chain information from a node."""
    base_url = f"http://{node_ip}:{port}"
    
    try:
        # Fetch metrics for chain length and latest hash
        metrics_response = requests.get(f"{base_url}/api/metrics", timeout=timeout)
        if metrics_response.status_code != 200:
            return None
        
        metrics = metrics_response.json()
        chain_length = metrics.get('blockchain_metrics', {}).get('total_blocks', 0)
        
        # Fetch latest block hash
        latest_hash = None
        if chain_length > 0:
            blocks_response = requests.get(
                f"{base_url}/api/blocks",
                params={'start_index': chain_length - 1, 'end_index': chain_length - 1},
                timeout=timeout
            )
            if blocks_response.status_code == 200:
                blocks = blocks_response.json()
                if blocks:
                    latest_hash = blocks[-1].get('hash')
        
        # Fetch all blocks to get chain hashes
        all_blocks_response = requests.get(f"{base_url}/api/blocks", timeout=timeout)
        block_hashes = []
        if all_blocks_response.status_code == 200:
            all_blocks = all_blocks_response.json()
            block_hashes = [(b.get('block_index', 0), b.get('hash')) for b in sorted(all_blocks, key=lambda x: x.get('block_index', 0))]
        
        return {
            'chain_length': chain_length,
            'latest_hash': latest_hash,
            'block_hashes': block_hashes,
            'status': 'online'
        }
    except requests.exceptions.RequestException as e:
        return {
            'chain_length': 0,
            'latest_hash': None,
            'block_hashes': [],
            'status': 'error',
            'error': str(e)
        }


def compare_chains(all_nodes_info: Dict[str, Dict]) -> Dict[str, any]:
    """Compare chains across all nodes and identify discrepancies."""
    results = {
        'all_same': True,
        'chain_lengths': {},
        'latest_hashes': {},
        'discrepancies': [],
        'consensus_summary': {}
    }
    
    # Extract chain lengths and latest hashes
    for node_id, info in all_nodes_info.items():
        results['chain_lengths'][node_id] = info.get('chain_length', 0)
        results['latest_hashes'][node_id] = info.get('latest_hash')
    
    # Find the most common chain length (should be all the same)
    length_counts = {}
    for length in results['chain_lengths'].values():
        length_counts[length] = length_counts.get(length, 0) + 1
    
    if not length_counts:
        results['all_same'] = False
        results['consensus_summary']['error'] = "No nodes responded"
        return results
    
    # Find consensus chain length (most common)
    consensus_length = max(length_counts.items(), key=lambda x: x[1])[0]
    results['consensus_summary']['consensus_length'] = consensus_length
    results['consensus_summary']['nodes_at_consensus'] = length_counts[consensus_length]
    results['consensus_summary']['total_nodes'] = len(all_nodes_info)
    
    # Check if all nodes have the same chain length
    if len(set(results['chain_lengths'].values())) > 1:
        results['all_same'] = False
        for node_id, length in results['chain_lengths'].items():
            if length != consensus_length:
                results['discrepancies'].append({
                    'node': node_id,
                    'issue': 'chain_length_mismatch',
                    'expected': consensus_length,
                    'actual': length
                })
    
    # Compare latest block hashes
    latest_hash_set = {h for h in results['latest_hashes'].values() if h is not None}
    if len(latest_hash_set) > 1:
        results['all_same'] = False
        # Find which nodes have different latest hashes
        consensus_latest_hash = max(
            (h for h in latest_hash_set),
            key=lambda h: sum(1 for v in results['latest_hashes'].values() if v == h),
            default=None
        )
        
        for node_id, hash_val in results['latest_hashes'].items():
            if hash_val != consensus_latest_hash and hash_val is not None:
                results['discrepancies'].append({
                    'node': node_id,
                    'issue': 'latest_hash_mismatch',
                    'expected': consensus_latest_hash,
                    'actual': hash_val
                })
    
    # Compare all block hashes (more thorough check)
    all_block_hashes = {}
    for node_id, info in all_nodes_info.items():
        all_block_hashes[node_id] = {idx: hash_val for idx, hash_val in info.get('block_hashes', [])}
    
    # Compare block by block
    if all_block_hashes:
        # Find the maximum block index across all nodes
        max_block_idx = max(
            (max(hashes.keys()) if hashes else -1)
            for hashes in all_block_hashes.values()
        )
        
        # Check each block index
        for block_idx in range(max_block_idx + 1):
            block_hashes_at_idx = {}
            for node_id, hashes in all_block_hashes.items():
                if block_idx in hashes:
                    block_hashes_at_idx[node_id] = hashes[block_idx]
            
            if block_hashes_at_idx:
                unique_hashes = set(block_hashes_at_idx.values())
                if len(unique_hashes) > 1:
                    results['all_same'] = False
                    consensus_hash = max(
                        unique_hashes,
                        key=lambda h: sum(1 for v in block_hashes_at_idx.values() if v == h)
                    )
                    
                    for node_id, hash_val in block_hashes_at_idx.items():
                        if hash_val != consensus_hash:
                            results['discrepancies'].append({
                                'node': node_id,
                                'issue': 'block_hash_mismatch',
                                'block_index': block_idx,
                                'expected': consensus_hash,
                                'actual': hash_val
                            })
    
    results['consensus_summary']['all_nodes_same'] = results['all_same']
    return results


def print_results(all_nodes_info: Dict[str, Dict], comparison_results: Dict):
    """Print verification results in a readable format."""
    print("=" * 80)
    print("BLOCKCHAIN CONSENSUS VERIFICATION")
    print("=" * 80)
    print()
    
    # Print node status
    print("NODE STATUS:")
    print("-" * 80)
    for node_id, info in sorted(all_nodes_info.items()):
        status = info.get('status', 'unknown')
        chain_len = info.get('chain_length', 0)
        latest_hash = info.get('latest_hash', 'N/A')
        
        if status == 'online':
            hash_preview = latest_hash[:16] + '...' if latest_hash and len(latest_hash) > 16 else latest_hash
            print(f"  {node_id:15} | Online | Chain Length: {chain_len:4} | Latest Hash: {hash_preview}")
        else:
            error = info.get('error', 'Unknown error')
            print(f"  {node_id:15} | ERROR  | {error}")
    print()
    
    # Print consensus summary
    summary = comparison_results.get('consensus_summary', {})
    print("CONSENSUS SUMMARY:")
    print("-" * 80)
    if 'error' in summary:
        print(f"  ERROR: {summary['error']}")
    else:
        total_nodes = summary.get('total_nodes', 0)
        consensus_length = summary.get('consensus_length', 0)
        nodes_at_consensus = summary.get('nodes_at_consensus', 0)
        all_same = summary.get('all_nodes_same', False)
        
        print(f"  Total Nodes: {total_nodes}")
        print(f"  Consensus Chain Length: {consensus_length}")
        print(f"  Nodes at Consensus Length: {nodes_at_consensus}/{total_nodes}")
        print(f"  All Nodes Have Same Chain: {'✓ YES' if all_same else '✗ NO'}")
    print()
    
    # Print discrepancies
    discrepancies = comparison_results.get('discrepancies', [])
    if discrepancies:
        print("DISCREPANCIES FOUND:")
        print("-" * 80)
        for disc in discrepancies:
            node = disc.get('node')
            issue = disc.get('issue')
            if issue == 'chain_length_mismatch':
                print(f"  {node}: Chain length mismatch (Expected: {disc.get('expected')}, Actual: {disc.get('actual')})")
            elif issue == 'latest_hash_mismatch':
                expected = disc.get('expected', '')[:16] + '...' if disc.get('expected') else 'N/A'
                actual = disc.get('actual', '')[:16] + '...' if disc.get('actual') else 'N/A'
                print(f"  {node}: Latest block hash mismatch")
                print(f"    Expected: {expected}")
                print(f"    Actual:   {actual}")
            elif issue == 'block_hash_mismatch':
                block_idx = disc.get('block_index')
                expected = disc.get('expected', '')[:16] + '...' if disc.get('expected') else 'N/A'
                actual = disc.get('actual', '')[:16] + '...' if disc.get('actual') else 'N/A'
                print(f"  {node}: Block #{block_idx} hash mismatch")
                print(f"    Expected: {expected}")
                print(f"    Actual:   {actual}")
        print()
    
    # Final verdict
    print("=" * 80)
    if comparison_results.get('all_same', False):
        print("VERDICT: ✓ ALL NODES HAVE THE SAME CHAIN (Consensus Achieved)")
    else:
        print("VERDICT: ✗ CHAIN MISMATCH DETECTED (Consensus Not Achieved)")
        print("         Some nodes may be on different forks or out of sync.")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Verify blockchain consensus across all nodes')
    parser.add_argument('--config', type=str, default='config/nodes.yaml',
                        help='Path to nodes.yaml configuration file (default: config/nodes.yaml)')
    parser.add_argument('--timeout', type=int, default=5,
                        help='Request timeout in seconds (default: 5)')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    
    config = load_config(str(config_path))
    nodes = config.get('nodes', [])
    
    if not nodes:
        print("Error: No nodes configured", file=sys.stderr)
        sys.exit(1)
    
    # Fetch chain info from all nodes
    print(f"Fetching chain information from {len(nodes)} nodes...")
    all_nodes_info = {}
    
    for node in nodes:
        node_id = node.get('id')
        node_ip = node.get('ip')
        dashboard_port = node.get('dashboard_port')
        
        if not all([node_id, node_ip, dashboard_port]):
            print(f"Warning: Skipping incomplete node config: {node}", file=sys.stderr)
            continue
        
        print(f"  Querying {node_id} ({node_ip}:{dashboard_port})...", end=' ')
        info = fetch_chain_info(node_ip, dashboard_port, timeout=args.timeout)
        
        if info and info.get('status') == 'online':
            print(f"✓ Chain length: {info.get('chain_length', 0)}")
        else:
            error_msg = info.get('error', 'Unknown error') if info else 'No response'
            print(f"✗ {error_msg}")
        
        all_nodes_info[node_id] = info
    
    print()
    
    # Compare chains
    comparison_results = compare_chains(all_nodes_info)
    
    # Output results
    if args.json:
        import json
        output = {
            'nodes': all_nodes_info,
            'comparison': comparison_results
        }
        print(json.dumps(output, indent=2))
    else:
        print_results(all_nodes_info, comparison_results)
    
    # Exit code
    sys.exit(0 if comparison_results.get('all_same', False) else 1)


if __name__ == '__main__':
    main()

