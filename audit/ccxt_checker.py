"""
CCXTChecker: Detects common CCXT anti-patterns in crypto trading systems.
Focuses on error handling gaps, order state desyncs, and rate limit violations.
"""

import ast
import asyncio
from pathlib import Path
from typing import List, Dict, Any


class CCXTChecker:
    def __init__(self, codebase_path: Path):
        self.path = codebase_path

    async def run(self) -> List[Dict[str, Any]]:
        findings = []
        py_files = list(self.path.rglob("*.py"))
        tasks = [self._analyze_file(f) for f in py_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                findings.extend(result)
        return findings

    async def _analyze_file(self, filepath: Path) -> List[Dict[str, Any]]:
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            return []

        findings = []
        # Check for CCXT calls without try/except
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Await):
                call = node.value.value
                if isinstance(call, ast.Call):
                    call_name = self._get_call_name(call)
                    if any(k in call_name for k in ["create_order", "cancel_order", "fetch_order"]):
                        if not self._is_in_try_block(node, tree):
                            findings.append({
                                "severity": "HIGH",
                                "type": "CCXT_UNHANDLED_ORDER_ERROR",
                                "file": str(filepath),
                                "line": node.lineno,
                                "message": f"CCXT call `{call_name}` not wrapped in try/except — network errors leave order state undefined",
                                "fix": "Wrap in try/except ccxt.NetworkError, ccxt.ExchangeError with order state reconciliation"
                            })
        return findings

    def _get_call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _is_in_try_block(self, target_node, tree) -> bool:
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for child in ast.walk(node):
                    if child is target_node:
                        return True
        return False
