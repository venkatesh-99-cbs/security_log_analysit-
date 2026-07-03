import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from .base import LogParser

SEVERITY_KEYWORDS = {
    "critical": "critical", "fatal": "critical", "emergency": "critical",
    "error": "high", "err": "high", "alert": "high",
    "warning": "medium", "warn": "medium",
    "notice": "low",
    "info": "info", "information": "info", "informational": "info",
    "debug": "info", "trace": "info",
}

CATEGORY_KEYWORDS = {
    "auth": "authentication", "login": "authentication", "logout": "authentication",
    "logon": "authentication", "ssh": "authentication", "password": "authentication",
    "sudo": "privilege_escalation", "privilege": "privilege_escalation",
    "firewall": "network", "connection": "network", "network": "network",
    "dns": "network", "http": "network", "request": "network",
    "process": "process", "exec": "process", "spawn": "process",
    "file": "file_system", "write": "file_system", "read": "file_system",
    "malware": "malware", "virus": "malware", "ransomware": "malware",
    "alert": "detection", "detection": "detection", "threat": "detection",
    "scan": "detection", "intrusion": "detection",
}

TIMESTAMP_FIELDS = ["timestamp", "ts", "time", "@timestamp", "datetime", "date", "created_at"]
SEVERITY_FIELDS = ["severity", "level", "log_level", "priority", "sev"]
MESSAGE_FIELDS = ["message", "msg", "text", "description", "event", "log"]
SOURCE_FIELDS = ["source", "host", "hostname", "src_ip", "client", "computer", "device"]
CATEGORY_FIELDS = ["category", "type", "event_type", "log_type", "action"]


def _extract_field(data: Dict, fields: List[str]) -> Optional[str]:
    for f in fields:
        if f in data:
            return str(data[f])
    return None


def _parse_timestamp(ts: Any) -> datetime:
    if isinstance(ts, (int, float)):
        # Unix timestamp (seconds or ms)
        if ts > 1e12:
            ts = ts / 1000
        try:
            return datetime.utcfromtimestamp(ts)
        except (OSError, OverflowError, ValueError):
            return datetime.utcnow()
    if isinstance(ts, str):
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
        ]:
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.utcnow()


def _detect_severity(text: str, level_field: Optional[str]) -> str:
    if level_field:
        key = level_field.lower().strip()
        if key in SEVERITY_KEYWORDS:
            return SEVERITY_KEYWORDS[key]
    if text:
        text_lower = text.lower()
        for keyword, severity in SEVERITY_KEYWORDS.items():
            if keyword in text_lower:
                return severity
    return "info"


def _detect_category(data: Dict, message: str) -> str:
    cat = _extract_field(data, CATEGORY_FIELDS)
    if cat:
        return cat.lower().replace(" ", "_")[:50]
    combined = message.lower()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in combined:
            return category
    return "general"


class JSONLogParser(LogParser):
    """Parses JSON and NDJSON log files (e.g., Suricata, Zeek, custom app logs)."""

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        raw_data = raw_data.strip()

        # NDJSON: one JSON object per line
        if raw_data.startswith("{"):
            for line in raw_data.splitlines():
                line = line.strip().rstrip(",")
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    parsed = self._parse_object(obj)
                    if parsed:
                        results.append(parsed)
                except json.JSONDecodeError:
                    continue
        else:
            # JSON array
            try:
                data = json.loads(raw_data)
                if isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict):
                            parsed = self._parse_object(obj)
                            if parsed:
                                results.append(parsed)
                elif isinstance(data, dict):
                    # Wrapped: {"events": [...]} or {"logs": [...]}
                    for key in ["events", "logs", "records", "data", "entries"]:
                        if key in data and isinstance(data[key], list):
                            for obj in data[key]:
                                parsed = self._parse_object(obj)
                                if parsed:
                                    results.append(parsed)
                            break
                    else:
                        parsed = self._parse_object(data)
                        if parsed:
                            results.append(parsed)
            except json.JSONDecodeError:
                pass

        return results

    def _parse_object(self, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(obj, dict):
            return None

        ts_raw = _extract_field(obj, TIMESTAMP_FIELDS)
        timestamp = _parse_timestamp(ts_raw) if ts_raw else datetime.utcnow()

        source = _extract_field(obj, SOURCE_FIELDS) or "unknown"
        level_raw = _extract_field(obj, SEVERITY_FIELDS)
        message_raw = _extract_field(obj, MESSAGE_FIELDS) or json.dumps(obj)[:300]
        severity = _detect_severity(message_raw, level_raw)
        category = _detect_category(obj, message_raw)

        return {
            "timestamp": timestamp,
            "source": source[:255],
            "category": category,
            "severity": severity,
            "message": message_raw[:1000],
            "raw_data": {k: v for k, v in obj.items() if not isinstance(v, (dict, list)) or len(str(v)) < 500},
        }

    def validate(self, data: Dict[str, Any]) -> bool:
        return "message" in data

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
