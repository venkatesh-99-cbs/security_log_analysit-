import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from .base import LogParser
from .json_log import (
    SEVERITY_KEYWORDS, CATEGORY_KEYWORDS,
    _parse_timestamp, _detect_severity, _detect_category
)

TIMESTAMP_COL_NAMES = {"timestamp", "ts", "time", "datetime", "date", "@timestamp", "created_at", "event_time"}
SEVERITY_COL_NAMES = {"severity", "level", "priority", "log_level", "sev", "risk_level"}
MESSAGE_COL_NAMES = {"message", "msg", "description", "event", "log", "text", "details", "action"}
SOURCE_COL_NAMES = {"source", "src", "src_ip", "source_ip", "host", "hostname", "client", "device", "computer"}
CATEGORY_COL_NAMES = {"category", "type", "event_type", "log_type", "class"}


def _best_column(headers: List[str], candidates: set) -> Optional[str]:
    for h in headers:
        if h.lower().strip() in candidates:
            return h
    return None


class CSVLogParser(LogParser):
    """Parses CSV firewall logs, access logs, and generic tabular log exports."""

    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        raw_data = raw_data.strip()
        if not raw_data:
            return results

        # Auto-detect delimiter (comma, tab, semicolon, pipe)
        sample = raw_data[:2000]
        delimiter = ","
        max_count = 0
        for delim in [",", "\t", ";", "|"]:
            count = sample.count(delim)
            if count > max_count:
                max_count = count
                delimiter = delim

        reader = csv.DictReader(io.StringIO(raw_data), delimiter=delimiter)
        try:
            headers = reader.fieldnames or []
        except Exception:
            return results

        ts_col = _best_column(list(headers), TIMESTAMP_COL_NAMES)
        sev_col = _best_column(list(headers), SEVERITY_COL_NAMES)
        msg_col = _best_column(list(headers), MESSAGE_COL_NAMES)
        src_col = _best_column(list(headers), SOURCE_COL_NAMES)
        cat_col = _best_column(list(headers), CATEGORY_COL_NAMES)

        for i, row in enumerate(reader):
            if i > 50000:  # Safety limit
                break
            try:
                parsed = self._parse_row(row, ts_col, sev_col, msg_col, src_col, cat_col)
                if parsed:
                    results.append(parsed)
            except Exception:
                continue

        return results

    def _parse_row(
        self, row: Dict[str, str],
        ts_col: Optional[str], sev_col: Optional[str],
        msg_col: Optional[str], src_col: Optional[str],
        cat_col: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not any(row.values()):
            return None

        ts_raw = row.get(ts_col) if ts_col else None
        timestamp = _parse_timestamp(ts_raw) if ts_raw else datetime.utcnow()

        source = (row.get(src_col, "unknown") if src_col else "unknown") or "unknown"

        level_raw = row.get(sev_col) if sev_col else None
        message_raw = (row.get(msg_col) if msg_col else None) or " | ".join(
            f"{k}={v}" for k, v in row.items() if v
        )
        severity = _detect_severity(message_raw, level_raw)

        category_raw = (row.get(cat_col) if cat_col else None)
        category = (category_raw.lower().replace(" ", "_")[:50] if category_raw
                    else _detect_category(row, message_raw))

        return {
            "timestamp": timestamp,
            "source": str(source)[:255],
            "category": category,
            "severity": severity,
            "message": str(message_raw)[:1000],
            "raw_data": {k: v for k, v in row.items() if v},
        }

    def validate(self, data: Dict[str, Any]) -> bool:
        return "message" in data

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
