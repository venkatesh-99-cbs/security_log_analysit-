"""
Anomaly Detector — statistical baseline anomaly detection.
Rule: Alert when the event rate for any source is >3× its rolling hourly average,
or when critical-severity event density spikes.
MITRE: T1499 — Endpoint Denial of Service (flooding variant)
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List
from .base import BaseDetector

SPIKE_MULTIPLIER = 3.0    # 3× baseline = anomaly
BASELINE_HOURS = 1        # use 1-hour buckets for baseline
MIN_BASELINE_EVENTS = 10  # need at least 10 events for a meaningful baseline
DENSITY_THRESHOLD = 50    # >50 critical/high events in 5 min = density spike


class AnomalyDetector(BaseDetector):
    """
    Statistical baseline anomaly detection.
    MITRE: T1499 — Endpoint Denial of Service
    """

    def detect(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []

        # Group logs by source and into hourly buckets
        source_buckets: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        all_ts_logs: List[Dict[str, Any]] = []

        for log in logs:
            ts = self._get_ts(log)
            bucket_key = ts.strftime("%Y-%m-%dT%H:00")
            source = log.get("source", "unknown")
            source_buckets[source][bucket_key].append(log)
            all_ts_logs.append(log)

        # Per-source rate anomaly
        for source, buckets in source_buckets.items():
            if len(buckets) < 2:
                continue

            bucket_counts = sorted([(k, len(v)) for k, v in buckets.items()])
            if len(bucket_counts) < 2:
                continue

            # Baseline = average of all-but-last bucket
            baseline_counts = [c for _, c in bucket_counts[:-1]]
            total = sum(baseline_counts)
            if total < MIN_BASELINE_EVENTS:
                continue

            avg = total / len(baseline_counts)
            last_key, last_count = bucket_counts[-1]
            last_logs = buckets[last_key]

            if avg > 0 and last_count >= avg * SPIKE_MULTIPLIER:
                alerts.append({
                    "type": "anomaly_rate_spike",
                    "severity": "medium",
                    "title": f"Event Rate Spike from {source}",
                    "description": (
                        f"Source '{source}' generated {last_count} events in hour {last_key}, "
                        f"which is {last_count/avg:.1f}× the baseline of {avg:.0f} events/hour."
                    ),
                    "source": source,
                    "current_rate": last_count,
                    "baseline_rate": round(avg, 2),
                    "multiplier": round(last_count / avg, 2),
                    "first_seen": self._get_ts(last_logs[0]).isoformat(),
                    "last_seen": self._get_ts(last_logs[-1]).isoformat(),
                    "event_count": last_count,
                    "mitre_technique": "T1499",
                    "mitre_tactic": "impact",
                    "log_ids": [e.get("id") for e in last_logs if e.get("id")],
                })

        # Critical/high event density spike (5-minute windows)
        high_sev = [
            l for l in all_ts_logs
            if l.get("severity") in ("critical", "high")
        ]
        if high_sev:
            high_sev_sorted = sorted(high_sev, key=lambda l: self._get_ts(l))
            window: List[Dict[str, Any]] = []
            for log in high_sev_sorted:
                ts = self._get_ts(log)
                cutoff = ts - timedelta(minutes=5)
                window = [e for e in window if self._get_ts(e) >= cutoff]
                window.append(log)
                if len(window) >= DENSITY_THRESHOLD:
                    alerts.append({
                        "type": "anomaly_critical_density",
                        "severity": "critical",
                        "title": "Critical Event Density Spike",
                        "description": (
                            f"Detected {len(window)} critical/high severity events "
                            f"within a 5-minute window — potential active attack."
                        ),
                        "event_count": len(window),
                        "first_seen": self._get_ts(window[0]).isoformat(),
                        "last_seen": self._get_ts(window[-1]).isoformat(),
                        "mitre_technique": "T1499",
                        "mitre_tactic": "impact",
                        "log_ids": [e.get("id") for e in window if e.get("id")],
                    })
                    window = []

        return alerts

    def _get_ts(self, event: Dict[str, Any]) -> datetime:
        ts = event.get("timestamp", datetime.utcnow())
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                return datetime.utcnow()
        return ts if isinstance(ts, datetime) else datetime.utcnow()
