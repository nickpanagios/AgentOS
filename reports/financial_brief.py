#!/usr/bin/env python3
"""Financial Brief — Warren's domain. BTC price + USD/EUR rate."""
import json, urllib.request
from datetime import date
from pathlib import Path

OUTPUT_DIR = Path(f"/home/executive-workspace/reports/output/{date.today()}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "AgentReporter/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def main():
    lines = [f"# Financial Brief — {date.today()}\n"]

    # BTC
    try:
        data = fetch_json("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        btc = data["bitcoin"]["usd"]
        lines.append(f"## Bitcoin\n\n- **BTC/USD**: ${btc:,.2f}\n")
    except Exception as e:
        lines.append(f"## Bitcoin\n\n- _Failed to fetch: {e}_\n")

    # USD/EUR
    try:
        data = fetch_json("https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR")
        eur = data["rates"]["EUR"]
        lines.append(f"## Forex\n\n- **USD/EUR**: {eur:.4f}\n- Date: {data.get('date', 'N/A')}\n")
    except Exception as e:
        lines.append(f"## Forex\n\n- _Failed to fetch: {e}_\n")

    report = "\n".join(lines)
    out = OUTPUT_DIR / "financial_brief.md"
    out.write_text(report)
    print(f"✅ Financial brief written to {out}")
    return report

if __name__ == "__main__":
    main()
