#!/usr/bin/env python3
"""
scanner.py - Async TCP connect network & port scanner

Usage examples:
    python3 scanner.py -t 192.168.1.10 -p 22,80,443
    python3 scanner.py -t 192.168.1.0/28 -p 1-1024 -c 500 --banner --output results.json
    python3 scanner.py -t example.com -p 80,443 --timeout 1.5

Only scan networks/hosts you own or have permission to test.
"""

import argparse
import asyncio
import csv
import ipaddress
import json
import socket
from typing import List, Tuple, Dict

DEFAULT_TIMEOUT = 1.0
DEFAULT_CONCURRENCY = 500
BANNER_READ_BYTES = 1024


def parse_ports(ports_arg: str) -> List[int]:
    ports = set()
    for part in ports_arg.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            a, b = int(a), int(b)
            if a > b:
                a, b = b, a
            ports.update(range(a, b + 1))
        else:
            ports.add(int(part))
    return sorted(p for p in ports if 1 <= p <= 65535)


def expand_targets(target_arg: str) -> List[str]:
    """
    Accepts:
      - single IPv4/IPv6 address
      - CIDR (e.g. 192.168.1.0/24)
      - hostname
    Returns a list of IP strings (IPv4/IPv6) or hostnames.
    """
    targets = []
    target_arg = target_arg.strip()
    # CIDR?
    try:
        if '/' in target_arg:
            net = ipaddress.ip_network(target_arg, strict=False)
            for ip in net.hosts():
                targets.append(str(ip))
            return targets
        # single IP?
        ipaddress.ip_address(target_arg)
        return [target_arg]
    except ValueError:
        # Not an IP/CIDR, treat as hostname
        return [target_arg]


async def banner_grab(reader: asyncio.StreamReader, timeout: float) -> str:
    try:
        data = await asyncio.wait_for(reader.read(BANNER_READ_BYTES), timeout=timeout)
        return data.decode(errors='replace').strip()
    except Exception:
        return ""


async def scan_port(host: str, port: int, timeout: float, do_banner: bool, sem: asyncio.Semaphore) -> Tuple[int, bool, str]:
    """
    Attempts TCP connect. Returns (port, is_open, banner)
    """
    async with sem:
        try:
            # Resolve: asyncio.open_connection accepts hostnames & IPs
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=timeout)
            banner = ""
            if do_banner:
                # try to read immediate bytes (many services send something)
                banner = await banner_grab(reader, timeout=min(0.5, timeout))
            writer.close()
            try:
                await writer.wait_closed()
            except AttributeError:
                # Python versions lacking wait_closed()
                pass
            return port, True, banner
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return port, False, ""
        except Exception:
            return port, False, ""


async def scan_host(host: str, ports: List[int], timeout: float, concurrency: int, do_banner: bool):
    sem = asyncio.Semaphore(concurrency)
    tasks = [scan_port(host, p, timeout, do_banner, sem) for p in ports]
    results = []
    # schedule and gather, but yield results progressively
    for coro in asyncio.as_completed(tasks):
        port, is_open, banner = await coro
        results.append((port, is_open, banner))
        if is_open:
            print(f"[{host}] OPEN  - {port}  {(' | ' + banner) if banner else ''}")
    return sorted(results, key=lambda x: x[0])


def save_json(outpath: str, data):
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_csv(outpath: str, data):
    # data: { host: [(port,is_open,banner), ...], ... }
    rows = []
    for host, results in data.items():
        for port, is_open, banner in results:
            rows.append({"host": host, "port": port, "open": is_open, "banner": banner})
    with open(outpath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["host", "port", "open", "banner"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def build_argparser():
    p = argparse.ArgumentParser(description="Async TCP connect network & port scanner")
    p.add_argument('-t', '--target', required=True, help="Target IP, CIDR (e.g. 192.168.1.0/24), or hostname")
    p.add_argument('-p', '--ports', required=True, help="Ports: comma list and/or ranges, e.g. 22,80,443,1000-2000")
    p.add_argument('-c', '--concurrency', type=int, default=DEFAULT_CONCURRENCY, help=f"Max concurrent connections (default {DEFAULT_CONCURRENCY})")
    p.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT, help=f"Per-connection timeout in seconds (default {DEFAULT_TIMEOUT})")
    p.add_argument('--banner', action='store_true', help="Attempt simple banner grabbing")
    p.add_argument('-o', '--output', help="Save results to JSON or CSV (filename with .json or .csv)")
    return p


async def main_async(args):
    ports = parse_ports(args.ports)
    targets = expand_targets(args.target)
    all_results: Dict[str, List[Tuple[int, bool, str]]] = {}

    for host in targets:
        print(f"Scanning {host} ... (ports: {len(ports)})")
        try:
            host_results = await scan_host(host, ports, args.timeout, args.concurrency, args.banner)
            all_results[host] = host_results
            open_count = sum(1 for (_, open_, _) in host_results if open_)
            print(f"Finished {host}: {open_count} open / {len(ports)} checked\n")
        except Exception as e:
            print(f"Error scanning {host}: {e}")

    # Output/save
    if args.output:
        if args.output.lower().endswith('.json'):
            serializable = {h: [{"port": p, "open": o, "banner": b} for (p, o, b) in res] for h, res in all_results.items()}
            save_json(args.output, serializable)
            print(f"Saved results to {args.output}")
        elif args.output.lower().endswith('.csv'):
            save_csv(args.output, all_results)
            print(f"Saved results to {args.output}")
        else:
            print("Output file must end with .json or .csv; skipping save.")

    return all_results


def main():
    parser = build_argparser()
    args = parser.parse_args()
    try:
        results = asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("Scan interrupted by user.")
    except Exception as e:
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
