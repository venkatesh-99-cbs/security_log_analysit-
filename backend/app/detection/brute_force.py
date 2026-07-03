"""
Brute Force Detector — detects repeated failed login attempts from a single source.
Rule: ≥5 failed authentications from the same source IP within a 5-minute window.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List
from .base import BaseDetector

FAILED_AUTH_KEYWORDS = [
    "failed logon", "failed login", "authentication failure",
    "invalid user", "invalid password", "logon failure",
    "4625",  # Windows EventID
    "failed password", "permission denied", "access denied",
    "bad password", "wrong password", "login incorrect",
]

THRESHOLD = 5
WINDOW_MINUTES = 5


class BruteForceDetector(BaseDetector):
    """
    Detects brute force login attacks.
    Fires an alert when a source IP generates ≥5 failed authentications within 5 minutes.
    MITRE: T1110 — Brute Force
    """

    def detect(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []

        # Group failed auth events by source IP
        failed_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for log in logs:
            if self._is_failed_auth(log):
                source = log.get("source", "unknown")
                failed_events[source].append(log)

        # Sliding window detection
        for source, events in failed_events.items():
            events_sorted = sorted(events, key=lambda e: e.get("timestamp", datetime.min))
            window: List[Dict[str, Any]] = []

            for event in events_sorted:
                ts = event.get("timestamp", datetime.utcnow())
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except ValueError:
                        ts = datetime.utcnow()

                # Remove events outside the window
                cutoff = ts - timedelta(minutes=WINDOW_MINUTES)
                window = [e for e in window if self._get_ts(e) >= cutoff]
                window.append(event)

                if len(window) >= THRESHOLD:
                    # Extract targeted usernames
                    targets = list({
                        e.get("raw_data", {}).get("extra", {}).get("TargetUserName") or
                        e.get("raw_data", {}).get("TargetUserName", "unknown")
                        for e in window
                    })
                    alerts.append({
                        "type": "brute_force",
                        "severity": "high",
                        "title": f"Brute Force Attack from {source}",
                        "description": (
                            f"Detected {len(window)} failed authentication attempts "
                            f"from {source} within {WINDOW_MINUTES} minutes. "
                            f"Targeted accounts: {', '.join(str(t) for t in targets[:5])}."
                        ),
                        "source_ip": source,
                        "affected_accounts": targets,
                        "event_count": len(window),
                        "first_seen": self._get_ts(window[0]).isoformat(),
                        "last_seen": self._get_ts(window[-1]).isoformat(),
                        "mitre_technique": "T1110",
                        "mitre_tactic": "credential_access",
                        "log_ids": [e.get("id") for e in window if e.get("id")],
                    })
                    # Clear window to avoid duplicate alerts for the same burst
                    window = []

        return alerts

    def _is_failed_auth(self, log: Dict[str, Any]) -> bool:
        message = (log.get("message") or "").lower()
        category = (log.get("category") or "").lower()
        raw = log.get("raw_data") or {}
        event_id = raw.get("event_id")

        # Windows failed logon
        if event_id == 4625:
            return True
        # Keyword-based
        return any(kw in message for kw in FAILED_AUTH_KEYWORDS)

    def _get_ts(self, event: Dict[str, Any]) -> datetime:
        ts = event.get("timestamp", datetime.utcnow())
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                return datetime.utcnow()
        return ts if isinstance(ts, datetime) else datetime.utcnow()
