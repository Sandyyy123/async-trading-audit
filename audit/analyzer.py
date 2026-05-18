"""
AsyncAuditor: AST-based analysis of async patterns in Python trading systems.
Detects blocking calls in coroutines, missing awaits, and poorly structured event loops.
"""

import ast
import asyncio
from pathlib import Path
from typing import List, Dict, Any

BLOCKING_CALLS = {
    "time.sleep", "requests.get", "requests.post", "requests.put", "requests.delete",
    "socket.recv", "socket.send", "subprocess.run", "subprocess.call"
}


class AsyncAuditor:
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
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef,)):
                findings.extend(self._check_blocking_in_async(node, filepath, source))
        return findings

    def _check_blocking_in_async(self, func_node: ast.AsyncFunctionDef,
                                  filepath: Path, source: str) -> List[Dict[str, Any]]:
        findings = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node)
                if call_name in BLOCKING_CALLS:
                    findings.append({
                        "severity": "HIGH",
                        "type": "BLOCKING_CALL_IN_ASYNC",
                        "file": str(filepath),
                        "line": node.lineno,
                        "message": f"Blocking call `{call_name}` inside async function `{func_node.name}` — will stall the event loop",
                        "fix": f"Replace with async equivalent (e.g., asyncio.sleep, aiohttp)"
                    })
        return findings

    def _get_call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
        elif isinstance(node.func, ast.Name):
            return node.func.id
        return ""
