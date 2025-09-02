from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - allow running without pyyaml installed
    yaml = None  # type: ignore


@dataclass
class Rule:
    name: str
    condition: str  # simple python expression over context
    points: int


class RuleEngine:
    def __init__(self, rules_path: Path | None = None) -> None:
        self.rules_path = rules_path or Path(__file__).with_name("rules.yaml")
        self.rules: Dict[str, List[Rule]] = {"aml": [], "fraud": []}
        self.version: int = 1
        self.metrics: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if yaml is None:
            # Fallback default rules if PyYAML not available
            self.rules = {
                "aml": [Rule("Large Cash Transaction", "amount > 10000", 30)],
                "fraud": [
                    Rule("High Velocity", "velocity_score_1h >= 10", 40),
                    Rule("Amount Spike", "z_score >= 3", 30),
                ],
            }
            return

        try:
            data = yaml.safe_load(self.rules_path.read_text())
            for category, entries in (data or {}).items():
                self.rules[category] = [
                    Rule(e.get("name"), e.get("condition"), int(e.get("points", 0)))
                    for e in entries or []
                ]
            self.version += 1
        except FileNotFoundError:
            self._load()  # fallback to defaults

    def evaluate(self, ctx: Dict[str, float]) -> Tuple[int, List[str]]:
        score = 0
        flags: List[str] = []
        # Very limited, safe eval context
        safe_ctx = {k: float(v) for k, v in ctx.items()}

        for category in ("aml", "fraud"):
            for rule in self.rules.get(category, []):
                try:
                    if bool(eval(rule.condition, {"__builtins__": {}}, safe_ctx)):
                        score += rule.points
                        flags.append(rule.name)
                        self.metrics[rule.name] = self.metrics.get(rule.name, 0) + 1
                except Exception:
                    # ignore broken rule expressions
                    continue
        return score, flags

    # CRUD and persistence
    def list_rules(self) -> Dict[str, List[Dict[str, object]]]:
        return {
            cat: [r.__dict__ for r in rules] for cat, rules in self.rules.items()
        }

    def add_rule(self, category: str, name: str, condition: str, points: int) -> None:
        rules = self.rules.setdefault(category, [])
        rules.append(Rule(name, condition, int(points)))
        self.version += 1
        self._save()

    def update_rule(self, category: str, name: str, condition: Optional[str] = None, points: Optional[int] = None) -> bool:
        rules = self.rules.get(category, [])
        for r in rules:
            if r.name == name:
                if condition is not None:
                    r.condition = condition
                if points is not None:
                    r.points = int(points)
                self.version += 1
                self._save()
                return True
        return False

    def delete_rule(self, category: str, name: str) -> bool:
        rules = self.rules.get(category, [])
        for i, r in enumerate(rules):
            if r.name == name:
                del rules[i]
                self.version += 1
                self._save()
                return True
        return False

    def _save(self) -> None:
        if yaml is None:
            return
        data = {}
        for cat, rules in self.rules.items():
            data[cat] = [r.__dict__ for r in rules]
        try:
            self.rules_path.write_text(yaml.safe_dump(data, sort_keys=False))
        except Exception:
            pass

    def get_metrics(self) -> Dict[str, int]:
        return dict(self.metrics)

    def reset_metrics(self) -> None:
        self.metrics.clear()
