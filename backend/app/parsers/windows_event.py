import xml.etree.ElementTree as ET
import re
from datetime import datetime
from typing import Any, Dict, List
from .base import LogParser

# Namespace used by Windows Event Log XML
_NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}

# EventID → severity mapping
SEVERITY_MAP: Dict[int, str] = {
    # Authentication
    4624: "info",   # Successful logon
    4625: "medium", # Failed logon
    4648: "medium", # Logon using explicit credentials
    4634: "info",   # Logoff
    4647: "info",   # User-initiated logoff
    4672: "high",   # Special privilege logon
    # Account management
    4720: "high",   # User account created
    4722: "medium", # User account enabled
    4723: "medium", # Password change attempt
    4724: "medium", # Password reset attempt
    4725: "high",   # User account disabled
    4726: "critical",# User account deleted
    4728: "high",   # Member added to security group
    4732: "high",   # Member added to local group
    4756: "high",   # Member added to universal group
    # Audit policy
    4719: "high",   # Audit policy changed
    4739: "high",   # Domain policy changed
    # Process
    4688: "info",   # Process created
    4689: "info",   # Process terminated
    # Network
    5140: "info",   # Network share accessed
    5145: "medium", # Network share checked
    # Logon failures
    4771: "medium", # Kerberos pre-auth failed
    4776: "medium", # DC auth attempt
}

CATEGORY_MAP: Dict[int, str] = {
    4624: "authentication", 4625: "authentication",
    4648: "authentication", 4634: "authentication",
    4647: "authentication", 4672: "privilege_escalation",
    4720: "account_management", 4722: "account_management",
    4723: "account_management", 4724: "account_management",
    4725: "account_management", 4726: "account_management",
    4728: "account_management", 4732: "account_management",
    4756: "account_management", 4719: "policy_change",
    4739: "policy_change", 4688: "process",
    4689: "process", 5140: "network",
    5145: "network", 4771: "authentication",
    4776: "authentication",
}


def _find(element: ET.Element, tag: str) -> str:
    """Helper: find text in a namespaced element."""
    el = element.find(tag, _NS)
    return el.text if el is not None and el.text else ""


def _data(event_data: ET.Element, name: str) -> str:
    """Extract named EventData field."""
    for d in event_data.findall("e:Data", _NS):
        if d.get("Name") == name:
            return d.text or ""
    return ""


class WindowsEventParser(LogParser):
    """Parses Windows Event Log XML files (single event or EventLog collection)."""

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        # Wrap in root if multiple events
        try:
            root = ET.fromstring(raw_data)
        except ET.ParseError:
            # Try wrapping bare events
            try:
                root = ET.fromstring(f"<Events>{raw_data}</Events>")
            except ET.ParseError:
                return self._parse_flat_events(raw_data)

        tag_local = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        events = []
        if tag_local == "Event":
            events = [root]
        elif tag_local in ("Events", "EventLog"):
            events = root.findall("e:Event", _NS) or root.findall("Event")
        else:
            events = root.findall(".//e:Event", _NS) or root.findall(".//Event")

        if not events and "EventID=" in raw_data:
            return self._parse_flat_events(raw_data)

        for event in events:
            parsed = self._parse_event(event)
            if parsed:
                results.append(parsed)

        return results

    def _parse_flat_events(self, raw_data: str) -> List[Dict[str, Any]]:
        """Parse exported key/value Windows records (EventID=4625 ...)."""
        results = []
        for line in raw_data.splitlines():
            match = re.match(r"(?P<timestamp>\S+\s+\S+)\s+(?P<body>.*)", line.strip())
            if not match or "EventID=" not in match.group("body"):
                continue
            fields = dict(re.findall(r"(\w+)=('.*?'|\".*?\"|\S+)", match.group("body")))
            try:
                event_id = int(fields.get("EventID", "0"))
                timestamp = datetime.fromisoformat(match.group("timestamp"))
            except (ValueError, TypeError):
                continue
            fields = {key: value.strip("'\"") for key, value in fields.items()}
            message = fields.get("Message", f"Windows Event {event_id}")
            results.append({
                "timestamp": timestamp, "source": fields.get("Computer", "unknown"),
                "category": CATEGORY_MAP.get(event_id, "system"),
                "severity": "critical" if event_id in (4732, 1116, 4740) else SEVERITY_MAP.get(event_id, "info"),
                "message": message,
                "raw_data": {"event_id": event_id, **fields},
                "event_id": event_id, "event_type": f"windows_{event_id}",
                "source_ip": fields.get("SourceIP"), "user": fields.get("User"),
                "hostname": fields.get("Computer"), "command_line": fields.get("CommandLine"),
            })
        return results

    def _parse_event(self, event: ET.Element) -> Dict[str, Any] | None:
        try:
            system = event.find("e:System", _NS) or event.find("System")
            if system is None:
                return None

            event_id_el = system.find("e:EventID", _NS) or system.find("EventID")
            event_id = int(event_id_el.text) if event_id_el is not None and event_id_el.text else 0

            time_created = system.find("e:TimeCreated", _NS) or system.find("TimeCreated")
            ts_str = time_created.get("SystemTime", "") if time_created is not None else ""
            try:
                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                timestamp = datetime.utcnow()

            computer_el = system.find("e:Computer", _NS) or system.find("Computer")
            computer = computer_el.text if computer_el is not None else "Unknown"

            channel_el = system.find("e:Channel", _NS) or system.find("Channel")
            channel = channel_el.text if channel_el is not None else "Security"

            # Extract EventData fields
            event_data = event.find("e:EventData", _NS) or event.find("EventData")
            extra: Dict[str, str] = {}
            if event_data is not None:
                for d in event_data.findall("e:Data", _NS) if _NS else event_data.findall("Data"):
                    name = d.get("Name", f"Data_{len(extra)}")
                    extra[name] = d.text or ""

            message = self._build_message(event_id, extra, computer)
            severity = SEVERITY_MAP.get(event_id, "info")
            category = CATEGORY_MAP.get(event_id, "system")

            return {
                "timestamp": timestamp,
                "source": computer,
                "category": category,
                "severity": severity,
                "message": message,
                "raw_data": {
                    "event_id": event_id,
                    "channel": channel,
                    "computer": computer,
                    "extra": extra,
                },
            }
        except Exception:
            return None

    def _build_message(self, event_id: int, extra: Dict[str, str], computer: str) -> str:
        templates = {
            4624: "Successful logon: user {TargetUserName} from {IpAddress}",
            4625: "Failed logon attempt: user {TargetUserName} from {IpAddress} (reason: {FailureReason})",
            4648: "Logon using explicit credentials by {SubjectUserName} targeting {TargetUserName}@{TargetServerName}",
            4672: "Special privileges assigned to {SubjectUserName}",
            4720: "User account created: {TargetUserName} by {SubjectUserName}",
            4726: "User account deleted: {TargetUserName} by {SubjectUserName}",
            4728: "Member {MemberName} added to global group {GroupName}",
            4688: "Process created: {NewProcessName} by {SubjectUserName}",
            4719: "Audit policy changed by {SubjectUserName}",
        }
        template = templates.get(event_id, f"Windows Event {event_id} on {computer}")
        try:
            return template.format_map({k: extra.get(k, "-") for k in re.findall(r"\{(\w+)\}", template)})
        except (KeyError, ValueError):
            return template

    def validate(self, data: Dict[str, Any]) -> bool:
        return "event_id" in data.get("raw_data", {})

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
