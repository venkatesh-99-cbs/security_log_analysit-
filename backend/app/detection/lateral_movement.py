"""
Lateral Movement Detector
Rules:
  - Same source user/IP authenticating successfully to ≥3 distinct hosts within 15 minutes
  - Windows EventID 4624 type 3 (network logon) or type 10 (remote interactive)
  - SMB / RDP connection keywords
MITRE: T1021 — Remote Services
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set
from .base import BaseDetector

NETWORK_LOGON_TYPES = {3, 10}   # 3=Network, 10=RemoteInteractive
LATERAL_KEYWORDS = [
    "smb", "rdp", "remote desktop", "psexec", "wmi", "winrm",
    "ssh", "telnet", "remote login", "net use", "ipc$",
]
REMOTE_SUCCESS_KEYWORDS = ["accepted password", "accepted publickey", "session opened for user"]
HOST_THRESHOLD = 3
WINDOW_MINUTES = 15


class LateralMovementDetector(BaseDetector):
    """
    Detects lateral movement patterns.
    MITRE: T1021 — Remote Services
    """

    def detect(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []

        # actor → list of (timestamp, target_host, log)
        actor_movements: Dict[str, List[tuple]] = defaultdict(list)

        for log in logs:
            actor, target = self._extract_movement(log)
            if actor and target and target != actor:
                actor_movements[actor].append((self._get_ts(log), target, log))

        for actor, movements in actor_movements.items():
            movements_sorted = sorted(movements, key=lambda x: x[0])
            window: List[tuple] = []

            for entry in movements_sorted:
                ts, target, log = entry
                cutoff = ts - timedelta(minutes=WINDOW_MINUTES)
                window = [e for e in window if e[0] >= cutoff]
                window.append(entry)

                unique_hosts: Set[str] = {e[1] for e in window}
                if len(unique_hosts) >= HOST_THRESHOLD:
                    logs_in_window = [e[2] for e in window]
                    alerts.append({
                        "type": "lateral_movement",
                        "severity": "critical",
                        "title": f"Lateral Movement: {actor}",
                        "description": (
                            f"Actor '{actor}' authenticated to {len(unique_hosts)} "
                            f"distinct hosts within {WINDOW_MINUTES} minutes: "
                            f"{', '.join(sorted(unique_hosts)[:10])}."
                        ),
                        "actor": actor,
                        "target_hosts": sorted(unique_hosts),
                        "host_count": len(unique_hosts),
                        "event_count": len(window),
                        "first_seen": window[0][0].isoformat(),
                        "last_seen": window[-1][0].isoformat(),
                        "mitre_technique": "T1021",
                        "mitre_tactic": "lateral_movement",
                        "log_ids": [e[2].get("id") for e in window if e[2].get("id")],
                    })
                    window = []  # Reset to avoid duplicate alerts

        return alerts

    def _extract_movement(self, log: Dict[str, Any]):
        raw = log.get("raw_data") or {}
        event_id = raw.get("event_id")
        message = (log.get("message") or "").lower()
        extra = raw.get("extra") or {}

        # Windows network logon (EventID 4624 type 3 or 10)
        if event_id == 4624:
            logon_type = int(extra.get("LogonType", 0))
            if logon_type in NETWORK_LOGON_TYPES:
                actor = extra.get("TargetUserName") or extra.get("SubjectUserName") or "unknown"
                target = extra.get("WorkstationName") or raw.get("computer") or "unknown"
                src_ip = extra.get("IpAddress", "-")
                if actor and actor not in ("-", "SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE"):
                    return f"{actor}@{src_ip}", target
            return None, None

        # Syslog remote auth success
        if any(kw in message for kw in REMOTE_SUCCESS_KEYWORDS):
            actor = log.get("source", "unknown")
            target = raw.get("hostname") or raw.get("computer") or "unknown"
            return actor, target

        # SMB/RDP keywords
        if any(kw in message for kw in LATERAL_KEYWORDS):
            actor = log.get("source", "unknown")
            target = raw.get("hostname") or "unknown"
            if actor != target:
                return actor, target

        return None, None

    def _get_ts(self, event: Dict[str, Any]) -> datetime:
        ts = event.get("timestamp", datetime.utcnow())
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                return datetime.utcnow()
        return ts if isinstance(ts, datetime) else datetime.utcnow()
