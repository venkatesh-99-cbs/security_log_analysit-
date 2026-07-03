import re
from datetime import datetime
from typing import Any, Dict, List
from .base import LogParser

# RFC 5424 syslog: <priority>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG
RFC5424_PATTERN = re.compile(
    r"<(?P<priority>\d+)>(?P<version>\d+)\s+"
    r"(?P<timestamp>\S+)\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<app_name>\S+)\s+"
    r"(?P<proc_id>\S+)\s+"
    r"(?P<msg_id>\S+)\s+"
    r"(?P<structured_data>\S+)\s?"
    r"(?P<message>.*)"
)

# BSD syslog: <priority>Mon  1 12:00:00 hostname program[pid]: message
BSD_PATTERN = re.compile(
    r"<(?P<priority>\d+)>?"
    r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(?P<day>\d+)\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<program>[^\[:]+)(?:\[(?P<pid>\d+)\])?:\s+"
    r"(?P<message>.*)"
)

# Plain syslog without priority
PLAIN_PATTERN = re.compile(
    r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(?P<day>\d+)\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<program>[^\[:]+)(?:\[(?P<pid>\d+)\])?:\s+"
    r"(?P<message>.*)"
)

FACILITY_NAMES = {
    0: "kernel", 1: "user", 2: "mail", 3: "daemon", 4: "auth",
    5: "syslog", 6: "lpr", 7: "news", 8: "uucp", 9: "cron",
    10: "authpriv", 16: "local0", 17: "local1", 18: "local2",
    19: "local3", 20: "local4", 21: "local5", 22: "local6", 23: "local7",
}

SEVERITY_FROM_PRIORITY = {
    0: "critical",  # Emergency
    1: "critical",  # Alert
    2: "critical",  # Critical
    3: "high",      # Error
    4: "medium",    # Warning
    5: "low",       # Notice
    6: "info",      # Informational
    7: "info",      # Debug
}

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

SECURITY_KEYWORDS = {
    "failed": "medium", "failure": "medium", "error": "medium",
    "invalid": "medium", "denied": "medium", "rejected": "medium",
    "unauthorized": "high", "breach": "critical", "attack": "high",
    "intrusion": "critical", "exploit": "critical", "malware": "critical",
    "sudo": "medium", "su:": "medium", "authentication failure": "high",
    "accepted password": "info", "accepted publickey": "info",
    "session opened": "info", "session closed": "info",
    "disconnect": "info", "connection closed": "info",
    "invalid user": "high", "did not receive identification": "medium",
}

CATEGORY_KEYWORDS = {
    "ssh": "authentication", "sshd": "authentication",
    "sudo": "privilege_escalation", "su": "privilege_escalation",
    "login": "authentication", "pam": "authentication",
    "kernel": "system", "systemd": "system",
    "cron": "scheduled_task", "crond": "scheduled_task",
    "firewall": "network", "iptables": "network", "nftables": "network",
    "auditd": "audit", "audit": "audit",
    "postfix": "network", "dovecot": "network",
}


def _parse_priority(priority: int):
    facility = priority >> 3
    severity_level = priority & 0x07
    return FACILITY_NAMES.get(facility, "unknown"), SEVERITY_FROM_PRIORITY.get(severity_level, "info")


def _detect_category(program: str, message: str) -> str:
    combined = (program + " " + message).lower()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in combined:
            return category
    return "system"


def _detect_severity(message: str, base_severity: str) -> str:
    msg_lower = message.lower()
    detected = base_severity
    severity_order = ["info", "low", "medium", "high", "critical"]
    for keyword, sev in SECURITY_KEYWORDS.items():
        if keyword in msg_lower:
            if severity_order.index(sev) > severity_order.index(detected):
                detected = sev
    return detected


def _parse_timestamp_bsd(month: str, day: str, time_str: str) -> datetime:
    now = datetime.utcnow()
    try:
        return datetime(
            year=now.year,
            month=MONTH_MAP.get(month, now.month),
            day=int(day),
            hour=int(time_str[:2]),
            minute=int(time_str[3:5]),
            second=int(time_str[6:8]),
        )
    except (ValueError, KeyError):
        return now


class LinuxSyslogParser(LogParser):
    """Parses RFC 5424, BSD syslog, and plain syslog formats."""

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for line in raw_data.splitlines():
            line = line.strip()
            if not line:
                continue
            parsed = self._parse_line(line)
            if parsed:
                results.append(parsed)
        return results

    def _parse_line(self, line: str) -> Dict[str, Any] | None:
        # Try RFC 5424
        m = RFC5424_PATTERN.match(line)
        if m:
            priority = int(m.group("priority"))
            facility_name, severity = _parse_priority(priority)
            ts_str = m.group("timestamp")
            try:
                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()
            hostname = m.group("hostname")
            program = m.group("app_name")
            message = m.group("message")
            category = _detect_category(program, message)
            severity = _detect_severity(message, severity)
            return {
                "timestamp": timestamp,
                "source": hostname,
                "category": category,
                "severity": severity,
                "message": message,
                "raw_data": {
                    "format": "rfc5424",
                    "priority": priority,
                    "facility": facility_name,
                    "program": program,
                    "proc_id": m.group("proc_id"),
                    "hostname": hostname,
                },
            }

        # Try BSD syslog
        m = BSD_PATTERN.match(line)
        if m:
            priority = int(m.group("priority")) if m.group("priority") else 30
            facility_name, severity = _parse_priority(priority)
            timestamp = _parse_timestamp_bsd(m.group("month"), m.group("day"), m.group("time"))
            hostname = m.group("hostname")
            program = m.group("program").strip()
            message = m.group("message")
            category = _detect_category(program, message)
            severity = _detect_severity(message, severity)
            return {
                "timestamp": timestamp,
                "source": hostname,
                "category": category,
                "severity": severity,
                "message": f"[{program}] {message}",
                "raw_data": {
                    "format": "bsd",
                    "facility": facility_name,
                    "program": program,
                    "pid": m.group("pid"),
                    "hostname": hostname,
                },
            }

        # Try plain syslog
        m = PLAIN_PATTERN.match(line)
        if m:
            timestamp = _parse_timestamp_bsd(m.group("month"), m.group("day"), m.group("time"))
            hostname = m.group("hostname")
            program = m.group("program").strip()
            message = m.group("message")
            category = _detect_category(program, message)
            severity = _detect_severity(message, "info")
            return {
                "timestamp": timestamp,
                "source": hostname,
                "category": category,
                "severity": severity,
                "message": f"[{program}] {message}",
                "raw_data": {
                    "format": "plain",
                    "program": program,
                    "pid": m.group("pid"),
                    "hostname": hostname,
                },
            }

        # Fallback: treat entire line as raw message
        return {
            "timestamp": datetime.utcnow(),
            "source": "unknown",
            "category": "system",
            "severity": "info",
            "message": line[:500],
            "raw_data": {"format": "unknown", "raw": line[:500]},
        }

    def validate(self, data: Dict[str, Any]) -> bool:
        return "message" in data and "timestamp" in data

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
