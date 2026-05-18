#!/usr/bin/env python3
"""
async-trading-audit: CLI entry point
Usage: python main.py --path /path/to/trading/system [--output report.json]
"""

import asyncio
import click
import json
from pathlib import Path
from audit.analyzer import AsyncAuditor
from audit.ccxt_checker import CCXTChecker
from audit.state_tracker import StateTracker


@click.command()
@click.option("--path", "-p", required=True, help="Path to trading system codebase")
@click.option("--output", "-o", default="audit_report.json", help="Output report path")
@click.option("--severity", "-s", default="LOW", type=click.Choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
              help="Minimum severity to include")
def main(path, output, severity):
    """Audit an async Python trading system for architectural issues."""
    asyncio.run(_run_audit(path, output, severity))


async def _run_audit(path: str, output: str, min_severity: str):
    codebase = Path(path)
    if not codebase.exists():
        click.echo(f"[ERROR] Path not found: {path}", err=True)
        return

    click.echo(f"[*] Starting audit of {path}...")

    auditor = AsyncAuditor(codebase)
    ccxt_checker = CCXTChecker(codebase)
    state_tracker = StateTracker(codebase)

    results = await asyncio.gather(
        auditor.run(),
        ccxt_checker.run(),
        state_tracker.run(),
    )

    findings = []
    for result in results:
        findings.extend(result)

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    min_level = severity_order[min_severity]
    filtered = [f for f in findings if severity_order.get(f["severity"], 3) <= min_level]
    filtered.sort(key=lambda x: severity_order.get(x["severity"], 3))

    report = {
        "summary": {
            "total_files_scanned": len(list(codebase.rglob("*.py"))),
            "total_findings": len(filtered),
            "by_severity": {
                sev: len([f for f in filtered if f["severity"] == sev])
                for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            }
        },
        "findings": filtered
    }

    with open(output, "w") as f:
        json.dump(report, f, indent=2)

    click.echo(f"\n[*] Audit complete. {len(filtered)} findings:")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = report["summary"]["by_severity"][sev]
        if count:
            click.echo(f"  {sev}: {count}")

    click.echo(f"\n[+] Report saved to {output}")


if __name__ == "__main__":
    main()
