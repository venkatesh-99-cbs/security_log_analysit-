"""
Privilege Escalation Detector
Rules:
  - Windows EventID 4672 (special privilege assigned)
  - sudo / su commands in syslog
  - Account added to privileged groups (EventID 4728, 4732, 4756)
MITRE: T1078 — Valid Accounts, T1548 — Abuse Elevation Control
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List
from .base import BaseDetector

PRIV_EVENT_IDS = {4672, 4728, 4732, 4756, 4720, 4724}
SUDO_KEYWORDS = ["sudo", "su:", "su -", "sudoers", "visudo", "runas", "privilege"]
PRIV_GROUP_KEYWORDS = ["administrators", "domain admins", "enterprise admins", "root", "wheel", "sudoers"]
BURST_THRESHOLD = 3          # alerts if same user escalates ≥3 times in 10 min
BURST_WINDOW_MINUTES = 10


class PrivilegeEscalationDetector(BaseDetector):
    """
    Detects privilege escalation events.
    MITRE: T1078, T1548
    """

    def detect(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        escalation_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for log in logs:
            actor, reason = self._is_privilege_escalation(log)
            if actor:
                log["_esc_actor"] = actor
                log["_esc_reason"] = reason
                escalation_events[actor].append(log)
                # Fire immediate alert for high-severity single events
                severity = log.get("severity", "info")
                if severity in ("high", "critical"):
                    alerts.append(self._build_alert(log, actor, reason, [log], "high"))

        # Burst detection: multiple escalations from same actor in window
        for actor, events in escalation_events.items():
            if len(events) < BURST_THRESHOLD:
                continue
            events_sorted = sorted(events, key=lambda e: self._get_ts(e))
            window: List[Dict[str, Any]] = []
            for event in events_sorted:
                ts = self._get_ts(event)
                cutoff = ts - timedelta(minutes=BURST_WINDOW_MINUTES)
                window = [e for e in window if self._get_ts(e) >= cutoff]
                window.append(event)
                if len(window) >= BURST_THRESHOLD:
                    alerts.append(self._build_alert(
                        event, actor, "Repeated privilege escalation", window, "critical"
                    ))
                    window = []

        return alerts

    def _is_privilege_escalation(self, log: Dict[str, Any]):
        raw = log.get("raw_data") or {}
        event_id = raw.get("event_id")
        message = (log.get("message") or "").lower()
        extra = raw.get("extra") or {}

        # Windows event IDs
        if event_id in PRIV_EVENT_IDS:
            actor = (extra.get("SubjectUserName") or extra.get("TargetUserName") or
                     raw.get("SubjectUserName") or "unknown")
            reasons = {
                4672: "Special privileges assigned to logon session",
                4728: f"Added to global group: {extra.get('GroupName', '?')}",
                4732: f"Added to local group: {extra.get('GroupName', '?')}",
                4756: f"Added to universal group: {extra.get('GroupName', '?')}",
                4720: f"New account created: {extra.get('TargetUserName', '?')}",
                4724: "Password reset attempt",
            }
            return actor, reasons.get(event_id, f"EventID {event_id}")

        # Syslog sudo/su
        if any(kw in message for kw in SUDO_KEYWORDS):
            actor = log.get("source", "unknown")
            if "sudo" in message:
                reason = "sudo command executed"
            elif "su:" in message or "su -" in message:
                reason = "su (switch user) executed"
            else:
                reason = "Privilege-related command"
            return actor, reason

        # Privilege group keywords
        if any(grp in message for grp in PRIV_GROUP_KEYWORDS):
            actor = log.get("source", "unknown")
            return actor, "Access to privileged group detected"

        return None, None

    def _build_alert(self, log, actor, reason, events, severity):
        return {
            "type": "privilege_escalation",
            "severity": severity,
            "title": f"Privilege Escalation: {actor}",
            "description": (
                f"Actor '{actor}' performed privilege escalation. "
                f"Reason: {reason}. "
                f"Occurred {len(events)} time(s)."
            ),
            "actor": actor,
            "reason": reason,
            "event_count": len(events),
            "first_seen": self._get_ts(events[0]).isoformat(),
            "last_seen": self._get_ts(events[-1]).isoformat(),
            "mitre_technique": "T1548",
            "mitre_tactic": "privilege_escalation",
            "log_ids": [e.get("id") for e in events if e.get("id")],
        }

    def _get_ts(self, event: Dict[str, Any]) -> datetime:
        ts = event.get("timestamp", datetime.utcnow())
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                return datetime.utcnow()
        return ts if isinstance(ts, datetime) else datetime.utcnow()
