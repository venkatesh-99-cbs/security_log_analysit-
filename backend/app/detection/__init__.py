"""
Detection Orchestrator — runs all detectors and aggregates alerts.
"""
from typing import Any, Dict, List
from .brute_force import BruteForceDetector
from .port_scan import PortScanDetector
from .privilege_escalation import PrivilegeEscalationDetector
from .lateral_movement import LateralMovementDetector
from .anomaly import AnomalyDetector
from .base import BaseDetector
from .rule_engine import RuleEngine


class DetectionOrchestrator:
    """
    Runs all registered detectors against a batch of logs and returns all alerts.
    """

    def __init__(self):
        self.detectors: List[BaseDetector] = [
            BruteForceDetector(),
            PortScanDetector(),
            PrivilegeEscalationDetector(),
            LateralMovementDetector(),
            AnomalyDetector(),
            RuleEngine(),
        ]

    def run_all(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute every detector and return the combined list of alerts.

        Args:
            logs: List of normalized log entry dicts from parsers.

        Returns:
            List of alert dicts, each with type, severity, title, description, etc.
        """
        all_alerts: List[Dict[str, Any]] = []
        for detector in self.detectors:
            try:
                alerts = detector.detect(logs)
                all_alerts.extend(alerts)
            except Exception as exc:
                # Log but don't crash — one detector failure shouldn't stop others
                import logging
                logging.getLogger(__name__).error(
                    "Detector %s failed: %s", detector.__class__.__name__, exc
                )
        return all_alerts


__all__ = [
    "BaseDetector",
    "BruteForceDetector",
    "PortScanDetector",
    "PrivilegeEscalationDetector",
    "LateralMovementDetector",
    "AnomalyDetector",
    "RuleEngine",
    "DetectionOrchestrator",
]
