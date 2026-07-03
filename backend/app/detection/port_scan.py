"""
Port Scan Detector — detects reconnaissance scanning activity.
Rule: ≥15 distinct destination ports from the same source IP within 2 minutes.
"""
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set
from .base import BaseDetector

PORT_PATTERN = re.compile(r"port[:\s]+(\d+)", re.IGNORECASE)
DST_PORT_KEYS = ["dst_port", "dest_port", "dport", "destination_port", "port"]
SRC_IP_KEYS = ["src_ip", "src", "source_ip", "client_ip", "remote_ip"]

PORT_THRESHOLD = 15
WINDOW_MINUTES = 2


class PortScanDetector(BaseDetector):
    """
    Detects port scanning activity.
    Fires when a source IP probes ≥15 distinct destination ports within 2 minutes.
    MITRE: T1046 — Network Service Discovery
    """

    def detect(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []

        # Group network events by source IP
        network_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for log in logs:
            port = self._extract_port(log)
            src = self._extract_src_ip(log)
            if port is not None and src and src != "unknown":
                log["_detected_port"] = port
                network_events[src].append(log)

        for src_ip, events in network_events.items():
            events_sorted = sorted(events, key=lambda e: self._get_ts(e))
            window: List[Dict[str, Any]] = []
            ports_in_window: List[int] = []

            for event in events_sorted:
                ts = self._get_ts(event)
                cutoff = ts - timedelta(minutes=WINDOW_MINUTES)

                # Expire old events
                new_window = []
                new_ports = []
                for e in window:
                    if self._get_ts(e) >= cutoff:
                        new_window.append(e)
                        new_ports.append(e.get("_detected_port", 0))
                window = new_window
                ports_in_window = new_ports

                window.append(event)
                ports_in_window.append(event.get("_detected_port", 0))

                unique_ports: Set[int] = set(ports_in_window)
                if len(unique_ports) >= PORT_THRESHOLD:
                    alerts.append({
                        "type": "port_scan",
                        "severity": "high",
                        "title": f"Port Scan Detected from {src_ip}",
                        "description": (
                            f"Source {src_ip} probed {len(unique_ports)} distinct ports "
                            f"within {WINDOW_MINUTES} minutes. "
                            f"Ports: {sorted(unique_ports)[:20]}."
                        ),
                        "source_ip": src_ip,
                        "scanned_ports": sorted(unique_ports),
                        "port_count": len(unique_ports),
                        "event_count": len(window),
                        "first_seen": self._get_ts(window[0]).isoformat(),
                        "last_seen": self._get_ts(window[-1]).isoformat(),
                        "mitre_technique": "T1046",
                        "mitre_tactic": "discovery",
                        "log_ids": [e.get("id") for e in window if e.get("id")],
                    })
                    window = []
                    ports_in_window = []

        return alerts

    def _extract_port(self, log: Dict[str, Any]) -> int | None:
        raw = log.get("raw_data") or {}
        for key in DST_PORT_KEYS:
            val = raw.get(key)
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass
        # Try message
        message = log.get("message", "")
        m = PORT_PATTERN.search(message)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return None

    def _extract_src_ip(self, log: Dict[str, Any]) -> str:
        raw = log.get("raw_data") or {}
        for key in SRC_IP_KEYS:
            val = raw.get(key)
            if val and val not in ("-", "*"):
                return str(val)
        return log.get("source", "unknown")

    def _get_ts(self, event: Dict[str, Any]) -> datetime:
        ts = event.get("timestamp", datetime.utcnow())
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                return datetime.utcnow()
        return ts if isinstance(ts, datetime) else datetime.utcnow()
