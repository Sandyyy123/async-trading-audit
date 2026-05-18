"""
StateTracker: Identifies shared mutable state accessed from multiple coroutines
without proper asyncio synchronization primitives.
"""

import ast
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict


class StateTracker:
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
        # Find class-level dicts/lists mutated inside async methods
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                shared_attrs = self._find_class_attrs(node)
                async_mutations = self._find_async_mutations(node, shared_attrs)
                if len(async_mutations) > 1:
                    attr_names = list(set(m["attr"] for m in async_mutations))
                    for attr in attr_names:
                        mutations = [m for m in async_mutations if m["attr"] == attr]
                        if len(mutations) > 1:
                            findings.append({
                                "severity": "CRITICAL",
                                "type": "SHARED_STATE_NO_LOCK",
                                "file": str(filepath),
                                "line": mutations[0]["line"],
                                "message": f"Class attribute `{attr}` mutated in {len(mutations)} async methods without asyncio.Lock — race condition risk",
                                "fix": "Protect all mutations with `async with self._lock:` (asyncio.Lock initialized in __init__)"
                            })
        return findings

    def _find_class_attrs(self, class_node: ast.ClassDef) -> Set[str]:
        attrs = set()
        for node in ast.walk(class_node):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                attrs.add(node.target.id)
        return attrs

    def _find_async_mutations(self, class_node: ast.ClassDef, attrs: Set[str]) -> List[Dict]:
        mutations = []
        for node in ast.walk(class_node):
            if isinstance(node, ast.AsyncFunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Attribute) and target.attr in attrs:
                                mutations.append({"attr": target.attr, "line": child.lineno, "func": node.name})
        return mutations
