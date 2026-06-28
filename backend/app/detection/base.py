from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..schemas.schemas import SecurityLog

class BaseDetector(ABC):
    """
    Interface for threat detection engines.
    """
    @abstractmethod
    def detect(self, logs: List[SecurityLog]) -> List[Dict[str, Any]]:
        """Run detection logic on a batch of logs."""
        pass

class BruteForceDetector(BaseDetector):
    def detect(self, logs: List[SecurityLog]) -> List[Dict[str, Any]]:
        # TODO: Implement brute force detection logic
        return []

class PortScanDetector(BaseDetector):
    def detect(self, logs: List[SecurityLog]) -> List[Dict[str, Any]]:
        # TODO: Implement port scan detection logic
        return []
