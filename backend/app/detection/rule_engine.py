"""Small external-rule engine for explainable, format-independent detections."""
import json
from pathlib import Path
from typing import Any, Dict, List
from .base import BaseDetector

class RuleEngine(BaseDetector):
    def __init__(self, path: str | None = None):
        rule_path = Path(path) if path else Path(__file__).with_name("rules.json")
        self.rules = json.loads(rule_path.read_text(encoding="utf-8"))

    def detect(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alerts = []
        for rule in self.rules:
            if rule.get("type") not in ("behavior", "event_id"):
                continue
            matched = [log for log in logs if self._matches(rule["id"], log)]
            if matched:
                alerts.append(self._alert(rule, matched))
        return alerts

    def _matches(self, rule_id: str, log: Dict[str, Any]) -> bool:
        text = " ".join(str(log.get(key, "")) for key in ("message", "event_type", "process", "command_line")).lower()
        event_id = str(log.get("event_id") or (log.get("raw_data") or {}).get("event_id") or "")
        rule = next((r for r in self.rules if r.get("id") == rule_id), {})
        if rule.get("type") == "event_id" and event_id != str(rule.get("event_id")):
            return False
        if rule.get("type") == "event_id" and rule.get("match"):
            return any(term in text for term in rule["match"].lower().split("|"))
        if rule.get("type") == "event_id":
            return True
        if rule_id == "EXEC-POWERSHELL-001":
            return "powershell" in text or "pwsh" in text
        if rule_id == "DEF-EVASION-001":
            return any(term in text for term in ("clear event log", "wevtutil cl", "audit log cleared", "event log service was stopped"))
        return False

    def _alert(self, rule: Dict[str, Any], matched: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "type": rule["id"], "rule_id": rule["id"], "rule_name": rule["name"],
            "severity": rule["severity"], "confidence": rule["confidence"],
            "mitre_technique": rule["mitre"], "event_count": len(matched),
            "source": matched[0].get("source", "unknown"),
            "log_ids": [log.get("id") for log in matched if log.get("id")],
            "evidence": [log.get("message", "")[:300] for log in matched[:5]],
            "description": f"{rule['name']} matched {len(matched)} normalized event(s). Evidence: {matched[0].get('message', '')[:300]}",
            "response_guidance": rule["response"],
            "first_seen": str(matched[0].get("timestamp", "")),
            "last_seen": str(matched[-1].get("timestamp", "")),
        }
