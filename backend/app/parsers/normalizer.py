"""Universal event normalization shared by every parser and detector."""
from datetime import datetime
from typing import Any, Dict

FIELD_ALIASES = {
    "hostname": ("hostname", "host", "computer", "device", "source"),
    "user": ("user", "username", "user_name", "account", "actor", "principal"),
    "source_ip": ("source_ip", "src_ip", "src", "client_ip", "remote_ip", "source"),
    "destination_ip": ("destination_ip", "dest_ip", "dst_ip", "destination", "target_ip"),
    "event_id": ("event_id", "eventid", "id", "signature_id", "rule_id"),
    "event_type": ("event_type", "event_name", "action", "type", "log_type"),
    "process": ("process", "process_name", "image", "application", "program"),
    "command_line": ("command_line", "cmdline", "command", "commandline"),
    "parent_process": ("parent_process", "parent_image", "parent_process_name"),
    "status": ("status", "result", "outcome", "state"),
    "vendor": ("vendor", "manufacturer"),
    "product": ("product", "product_name", "service"),
}

def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    raw = event.get("raw_data") or {}
    source = {**raw, **event}
    normalized = dict(event)
    for canonical, aliases in FIELD_ALIASES.items():
        value = next((source.get(key) for key in aliases if source.get(key) not in (None, "")), None)
        if value is not None:
            normalized[canonical] = str(value)[:500] if not isinstance(value, (int, float)) else value
    normalized.setdefault("hostname", normalized.get("source", "unknown"))
    normalized.setdefault("user", "unknown")
    normalized.setdefault("event_type", normalized.get("category", "general"))
    normalized.setdefault("message", "")
    normalized.setdefault("severity", "info")
    normalized.setdefault("category", "general")
    normalized.setdefault("raw_log", normalized.get("message", ""))
    return normalized
