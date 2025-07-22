"""
Debug Logger for Hybrid Interactive Mode
Captures processing logs for in-app visibility
"""

import datetime
from collections import deque
from typing import Dict, List, Any
import threading

class DebugLogger:
    """Thread-safe debug logger for capturing hybrid system processing"""
    
    def __init__(self, max_entries=100):
        self.max_entries = max_entries
        self.logs = deque(maxlen=max_entries)
        self.lock = threading.Lock()
    
    def log(self, category: str, message: str, data: Dict[str, Any] = None):
        """Add a debug log entry"""
        with self.lock:
            entry = {
                'timestamp': datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3],
                'category': category,
                'message': message,
                'data': data or {}
            }
            self.logs.append(entry)
    
    def get_logs(self, limit: int = None) -> List[Dict]:
        """Get recent log entries"""
        with self.lock:
            logs_list = list(self.logs)
            if limit:
                return logs_list[-limit:]
            return logs_list
    
    def clear(self):
        """Clear all logs"""
        with self.lock:
            self.logs.clear()

# Global debug logger instance
debug_logger = DebugLogger()
