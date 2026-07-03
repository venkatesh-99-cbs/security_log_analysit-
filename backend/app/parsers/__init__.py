"""
Log Parser Dispatcher — auto-detects format and returns parsed log entries.
"""
from typing import Any, Dict, List, Optional
from .base import LogParser
from .windows_event import WindowsEventParser
from .linux_syslog import LinuxSyslogParser
from .json_log import JSONLogParser
from .csv_log import CSVLogParser


def detect_format(raw_data: str) -> str:
    """Heuristically detect the log format from the raw content."""
    sample = raw_data.strip()[:2000]
    
    # Windows Event XML
    if "<Event" in sample or "<EventLog" in sample or (
        "xmlns" in sample and "events/event" in sample
    ):
        return "windows_event"
    
    # JSON / NDJSON
    stripped = sample.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    
    # RFC 5424 syslog (starts with <priority>version)
    import re
    if re.match(r"<\d+>\d+\s+\S+T\S+\s+\S+", sample):
        return "syslog"
    
    # BSD / plain syslog
    if re.match(r"<?\d*>?\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+", sample):
        return "syslog"
    
    # CSV: has commas/tabs and multiple fields per line
    lines = sample.splitlines()
    if lines:
        first_meaningful = next((l for l in lines if l.strip()), "")
        comma_count = first_meaningful.count(",")
        tab_count = first_meaningful.count("\t")
        pipe_count = first_meaningful.count("|")
        semicolon_count = first_meaningful.count(";")
        if max(comma_count, tab_count, pipe_count, semicolon_count) >= 3:
            return "csv"
    
    # Default to syslog (most permissive plain-text parser)
    return "syslog"


def get_parser(format_hint: Optional[str] = None) -> LogParser:
    """Return the appropriate parser for a given format hint."""
    parsers = {
        "windows_event": WindowsEventParser,
        "syslog": LinuxSyslogParser,
        "json": JSONLogParser,
        "csv": CSVLogParser,
    }
    cls = parsers.get(format_hint or "", LinuxSyslogParser)
    return cls()


def parse_log_file(raw_data: str, filename: str = "") -> List[Dict[str, Any]]:
    """
    Parse raw log file content. Auto-detects format from content and filename extension.
    
    Args:
        raw_data: Raw text content of the log file.
        filename: Original filename (used as a secondary hint).
    
    Returns:
        List of normalized log entry dicts.
    """
    # Extension-based hint
    ext_hint: Optional[str] = None
    if filename:
        fn_lower = filename.lower()
        if fn_lower.endswith((".xml", ".evtx")):
            ext_hint = "windows_event"
        elif fn_lower.endswith(".json") or fn_lower.endswith(".ndjson"):
            ext_hint = "json"
        elif fn_lower.endswith(".csv") or fn_lower.endswith(".tsv"):
            ext_hint = "csv"
        elif fn_lower.endswith((".log", ".syslog", ".txt")):
            ext_hint = "syslog"
    
    # Content-based detection
    content_format = detect_format(raw_data)
    
    # Prefer extension hint if available
    chosen_format = ext_hint or content_format
    parser = get_parser(chosen_format)
    
    results = parser.parse(raw_data)
    
    # Fallback: if primary parser returned nothing, try others
    if not results:
        for fallback_format in ["syslog", "json", "csv", "windows_event"]:
            if fallback_format != chosen_format:
                try:
                    results = get_parser(fallback_format).parse(raw_data)
                    if results:
                        break
                except Exception:
                    continue
    
    return results


__all__ = [
    "LogParser", "WindowsEventParser", "LinuxSyslogParser",
    "JSONLogParser", "CSVLogParser", "parse_log_file", "detect_format", "get_parser"
]
