# Network & Port Scanner `scanner.py`

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg) ![License: MIT](https://img.shields.io/badge/license-MIT-green.svg) ![Lines](https://img.shields.io/badge/lines-~300-orange.svg) ![Tests](https://img.shields.io/badge/tests-none-lightgrey.svg)

A compact, practical **asynchronous TCP connect** network & port scanner written in Python (single-file). Fast, cross-platform, and no special privileges required — uses `asyncio.open_connection` for concurrent connect-scans and optional banner grabbing.

> ⚠️ **Only scan systems and networks you own or have explicit permission to test.** Unauthorized scanning can be illegal and/or disruptive.

---

## Demo

> Add a short animated GIF to the repository at `./demo.gif` (10–500 KB recommended) and GitHub will render it in the README. Example embed below — replace with your GIF file.

![Demo](./demo.gif)

*If you don't have a GIF yet, create one by recording a terminal session (e.g., using `asciinema` + `svg2gif` or `peek` on Linux, or `ShareX` on Windows), then add it to the repo.*

---

## Badges (customize)

You can replace `<OWNER>` and `<REPO>` below with your GitHub account and repository name to enable workflow badges.

```markdown
![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/<OWNER>/<REPO>)
```

---

## Features

* Accepts single IP, hostname, or CIDR (e.g. `192.168.1.0/24`) targets.
* Port specification with commas and ranges (e.g. `22,80,443,1000-1010`).
* High-concurrency async TCP connect scanning (no raw sockets, no root required).
* Optional simple banner grabbing (reads greeting bytes after connect).
* Progressive console output (prints open ports as found).
* Save results to JSON or CSV.
* No external dependencies — standard library only.

---

## Requirements

* Python 3.8 or newer

---

## Install / Add to repo

1. Save the scanner to `scanner.py` in your repository.
2. (Optional) Add a small demo GIF as `demo.gif`.
3. Make executable (optional):

```bash
chmod +x scanner.py
```

---

## Usage

```text
usage: scanner.py -t TARGET -p PORTS [options]

Required:
  -t, --target      Target IP, CIDR (e.g. 192.168.1.0/24), or hostname
  -p, --ports       Ports: comma list and/or ranges, e.g. 22,80,443,1000-2000

Options:
  -c, --concurrency Max concurrent connections (default 500)
  --timeout         Per-connection timeout in seconds (default 1.0)
  --banner          Attempt simple banner grabbing
  -o, --output      Save results to JSON or CSV (filename ending with .json or .csv)
```

### Examples

Single host scan:

```bash
python3 scanner.py -t 192.168.1.10 -p 22,80,443
```

CIDR scan with port range, banners, and JSON output:

```bash
python3 scanner.py -t 192.168.1.0/28 -p 1-1024 --banner -c 500 -o results.json
```

Hostname scan with shorter timeout:

```bash
python3 scanner.py -t example.com -p 80,443 --timeout 0.8
```

---

## Output examples

**Console**

```
Scanning 192.168.1.10 ... (ports: 3)
[192.168.1.10] OPEN  - 22  OpenSSH_7.4p1 Debian-10+deb9u7
[192.168.1.10] OPEN  - 80  Apache/2.4.25 (Debian)
Finished 192.168.1.10: 2 open / 3 checked
Saved results to results.json
```

**JSON** (`-o results.json`)

```json
{
  "192.168.1.10": [
    {"port": 22, "open": true, "banner": "OpenSSH_7.4p1 Debian-10+deb9u7"},
    {"port": 80, "open": true, "banner": "Apache/2.4.25 (Debian)"},
    {"port": 443, "open": false, "banner": ""}
  ]
}
```

---

## How it works (short)

* **Target expansion**: `ipaddress` expands CIDRs to host IPs; hostnames are left as-is (resolved by `asyncio`).
* **Ports parsing**: accepts lists and ranges; validates ports `1..65535`.
* **Scanning**: `asyncio.open_connection(host, port)` does the TCP connect. A semaphore bounds concurrent in-flight connections.
* **Banner grabbing**: if enabled, reads up to a fixed byte count from the socket after connect. (Note: many protocols require sending a request to elicit a banner — e.g., HTTP needs a GET.)

---

## Tuning & tips

* **Concurrency**: increase `-c` to speed up port scans (but watch system limits and network noise). Default is `500`.
* **Timeout**: use lower values for LAN scans (`0.5`) and higher values for remote or flaky hosts.
* **Large CIDRs**: avoid scanning huge subnets (e.g., `/16`) unless you intend to wait — memory & time grow fast.
* **Banner accuracy**: for accurate HTTP/TLS banners, send protocol-aware probes (HTTP GET, TLS handshake) rather than relying on immediate server greeting.

---

## Troubleshooting

* If all ports appear closed or time out, check network reachability (ping/traceroute) and local firewall rules.
* If you hit OS limits (`Too many open files`), reduce concurrency or increase `ulimit -n`.

---

## Roadmap / Improvements

* Protocol-aware banner probes (HTTP, SMTP, TLS SNI).
* Global concurrency across multi-host scans.
* Retries with backoff for transient failures.
* UDP scanning & ICMP handling (requires different approaches/privileges).
* Terminal UI / progress bars.

---

## Contributing

Bug reports and PRs welcome. Please include a short description, reproduction steps, and example outputs for fixes.

---

## License

This repository is provided for educational and authorized testing purposes. Add a `LICENSE` file (e.g., MIT) if you want to make the license explicit.

---

*Generated with ❤️ — edit as needed and replace placeholders like `<OWNER>/<REPO>` and `demo.gif`.*
