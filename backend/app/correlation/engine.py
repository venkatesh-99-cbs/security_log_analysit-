"""
Correlation Engine, Threat Scoring, and MITRE ATT&CK Mapper.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# MITRE ATT&CK technique dictionary (curated subset)
# ---------------------------------------------------------------------------
MITRE_TECHNIQUES: Dict[str, Dict[str, str]] = {
    # Credential Access
    "T1110": {"name": "Brute Force", "tactic": "Credential Access", "tactic_id": "TA0006"},
    "T1110.001": {"name": "Password Guessing", "tactic": "Credential Access", "tactic_id": "TA0006"},
    "T1110.003": {"name": "Password Spraying", "tactic": "Credential Access", "tactic_id": "TA0006"},
    "T1003": {"name": "OS Credential Dumping", "tactic": "Credential Access", "tactic_id": "TA0006"},
    "T1552": {"name": "Unsecured Credentials", "tactic": "Credential Access", "tactic_id": "TA0006"},
    # Discovery
    "T1046": {"name": "Network Service Discovery", "tactic": "Discovery", "tactic_id": "TA0007"},
    "T1083": {"name": "File and Directory Discovery", "tactic": "Discovery", "tactic_id": "TA0007"},
    "T1057": {"name": "Process Discovery", "tactic": "Discovery", "tactic_id": "TA0007"},
    "T1018": {"name": "Remote System Discovery", "tactic": "Discovery", "tactic_id": "TA0007"},
    "T1087": {"name": "Account Discovery", "tactic": "Discovery", "tactic_id": "TA0007"},
    # Privilege Escalation
    "T1548": {"name": "Abuse Elevation Control Mechanism", "tactic": "Privilege Escalation", "tactic_id": "TA0004"},
    "T1078": {"name": "Valid Accounts", "tactic": "Privilege Escalation", "tactic_id": "TA0004"},
    "T1098": {"name": "Account Manipulation", "tactic": "Privilege Escalation", "tactic_id": "TA0004"},
    # Lateral Movement
    "T1021": {"name": "Remote Services", "tactic": "Lateral Movement", "tactic_id": "TA0008"},
    "T1021.001": {"name": "Remote Desktop Protocol", "tactic": "Lateral Movement", "tactic_id": "TA0008"},
    "T1021.002": {"name": "SMB/Windows Admin Shares", "tactic": "Lateral Movement", "tactic_id": "TA0008"},
    "T1021.004": {"name": "SSH", "tactic": "Lateral Movement", "tactic_id": "TA0008"},
    "T1075": {"name": "Pass the Hash", "tactic": "Lateral Movement", "tactic_id": "TA0008"},
    # Impact
    "T1499": {"name": "Endpoint Denial of Service", "tactic": "Impact", "tactic_id": "TA0040"},
    "T1485": {"name": "Data Destruction", "tactic": "Impact", "tactic_id": "TA0040"},
    # Persistence
    "T1136": {"name": "Create Account", "tactic": "Persistence", "tactic_id": "TA0003"},
    "T1098": {"name": "Account Manipulation", "tactic": "Persistence", "tactic_id": "TA0003"},
    # Initial Access
    "T1190": {"name": "Exploit Public-Facing Application", "tactic": "Initial Access", "tactic_id": "TA0001"},
    "T1078": {"name": "Valid Accounts", "tactic": "Initial Access", "tactic_id": "TA0001"},
}

DETECTION_TYPE_TO_MITRE: Dict[str, List[str]] = {
    "brute_force": ["T1110", "T1110.001"],
    "port_scan": ["T1046", "T1018"],
    "privilege_escalation": ["T1548", "T1078"],
    "lateral_movement": ["T1021", "T1021.001", "T1021.002", "T1021.004"],
    "anomaly_rate_spike": ["T1499"],
    "anomaly_critical_density": ["T1499"],
}

SEVERITY_WEIGHTS = {"critical": 10, "high": 7, "medium": 4, "low": 2, "info": 1}
CORR_WINDOW_MINUTES = 30


class CorrelationEngine:
    """
    Correlates alerts (from detectors) with logs into Incident records.
    Groups alerts by common source IP or actor within a time window.
    """

    def correlate(
        self,
        logs: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of incident dicts ready to be saved to the DB.
        """
        if not alerts:
            return []

        incidents: List[Dict[str, Any]] = []
        alerts_sorted = sorted(alerts, key=lambda a: a.get("first_seen") or "")

        # Group alerts by actor/source within time windows
        groups: List[List[Dict[str, Any]]] = []
        used = set()

        for i, alert in enumerate(alerts_sorted):
            if i in used:
                continue
            group = [alert]
            used.add(i)
            ts_i = self._parse_ts(alert.get("first_seen"))
            src_i = self._alert_source(alert)

            for j, other in enumerate(alerts_sorted):
                if j in used or j == i:
                    continue
                ts_j = self._parse_ts(other.get("first_seen"))
                src_j = self._alert_source(other)
                time_close = abs((ts_i - ts_j).total_seconds()) <= CORR_WINDOW_MINUTES * 60
                same_src = src_i != "unknown" and src_i == src_j
                if time_close and same_src:
                    group.append(other)
                    used.add(j)

            groups.append(group)

        scorer = ThreatScoringEngine()
        mitre_mapper = MITREMapper()

        for group in groups:
            severity = self._group_severity(group)
            score = scorer.calculate_score_from_alerts(group)
            mitre_mappings = []
            for alert in group:
                mitre_mappings.extend(mitre_mapper.map_to_mitre(alert))

            # Deduplicate mitre mappings
            seen_mitre = set()
            unique_mitre = []
            for m in mitre_mappings:
                key = m["technique_id"]
                if key not in seen_mitre:
                    seen_mitre.add(key)
                    unique_mitre.append(m)

            source = self._alert_source(group[0])
            types = list({a.get("type", "unknown") for a in group})
            title = self._build_title(group, source, types)

            incidents.append({
                "title": title,
                "description": self._build_description(group, source),
                "status": "open",
                "severity": severity,
                "threat_score": score,
                "source_ip": source,
                "alert_count": len(group),
                "alert_types": types,
                "mitre_mappings": unique_mitre,
                "first_seen": min(
                    a.get("first_seen") or "" for a in group
                ),
                "last_seen": max(
                    a.get("last_seen") or "" for a in group
                ),
                "log_ids": list({
                    lid for a in group for lid in (a.get("log_ids") or []) if lid
                }),
            })

        return incidents

    def _alert_source(self, alert: Dict[str, Any]) -> str:
        return (alert.get("source_ip") or alert.get("actor") or
                alert.get("source") or "unknown")

    def _group_severity(self, group: List[Dict[str, Any]]) -> str:
        order = ["info", "low", "medium", "high", "critical"]
        max_sev = "info"
        for alert in group:
            sev = alert.get("severity", "info")
            if order.index(sev) > order.index(max_sev):
                max_sev = sev
        return max_sev

    def _build_title(self, group, source, types) -> str:
        type_labels = {
            "brute_force": "Brute Force Attack",
            "port_scan": "Port Scan",
            "privilege_escalation": "Privilege Escalation",
            "lateral_movement": "Lateral Movement",
            "anomaly_rate_spike": "Event Rate Anomaly",
            "anomaly_critical_density": "Critical Alert Density",
        }
        labels = [type_labels.get(t, t.replace("_", " ").title()) for t in types]
        if len(labels) == 1:
            title = labels[0]
        elif len(labels) == 2:
            title = " & ".join(labels)
        else:
            title = f"Multi-Stage Attack ({len(labels)} techniques)"
        return f"{title} — {source}" if source != "unknown" else title

    def _build_description(self, group, source) -> str:
        lines = [f"Correlated {len(group)} alert(s) from source '{source}'."]
        for alert in group[:5]:
            lines.append(f"• {alert.get('description', '')}")
        return "\n".join(lines)

    def _parse_ts(self, ts_str: Optional[str]) -> datetime:
        if not ts_str:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()


class ThreatScoringEngine:
    """Calculates a 0–100 threat score for an incident."""

    def calculate_score(self, incident: Dict[str, Any]) -> float:
        alerts = incident.get("alerts", [])
        return self.calculate_score_from_alerts(alerts)

    def calculate_score_from_alerts(self, alerts: List[Dict[str, Any]]) -> float:
        if not alerts:
            return 0.0

        base_scores = [SEVERITY_WEIGHTS.get(a.get("severity", "info"), 1) for a in alerts]
        raw = sum(base_scores)

        # Bonus for multi-technique correlation
        technique_count = len({a.get("type") for a in alerts})
        multi_technique_bonus = min(technique_count * 5, 20)

        # Bonus for high event counts
        total_events = sum(a.get("event_count", 1) for a in alerts)
        volume_bonus = min(total_events / 10, 15)

        score = raw + multi_technique_bonus + volume_bonus
        return min(round(score, 1), 100.0)


class MITREMapper:
    """Maps alert detection types to MITRE ATT&CK techniques."""

    def map_to_mitre(self, alert: Dict[str, Any]) -> List[Dict[str, str]]:
        detection_type = alert.get("type", "")
        technique_ids = DETECTION_TYPE_TO_MITRE.get(detection_type, [])

        # Also check if alert already has a technique ID
        existing = alert.get("mitre_technique")
        if existing and existing not in technique_ids:
            technique_ids = [existing] + technique_ids

        results = []
        for tid in technique_ids:
            tech = MITRE_TECHNIQUES.get(tid)
            if tech:
                results.append({
                    "technique_id": tid,
                    "technique_name": tech["name"],
                    "tactic": tech["tactic"],
                    "tactic_id": tech["tactic_id"],
                })
        return results
