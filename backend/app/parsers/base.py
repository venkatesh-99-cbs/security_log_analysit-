from abc import ABC, abstractmethod
from typing import Any, Dict, List

class LogParser(ABC):
    """
    Abstract interface for all security log parsers.
    """
    @abstractmethod
    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        """Parse raw log data into a list of normalized dictionaries."""
        pass

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate if the data matches the expected format."""
        pass

    @abstractmethod
    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parsed data into a standard schema."""
        pass

class WindowsEventParser(LogParser):
    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        # TODO: Implement Windows Event Log parsing
        return []

    def validate(self, data: Dict[str, Any]) -> bool:
        return True

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data

class LinuxSyslogParser(LogParser):
    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        # TODO: Implement Syslog parsing
        return []

    def validate(self, data: Dict[str, Any]) -> bool:
        return True

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
