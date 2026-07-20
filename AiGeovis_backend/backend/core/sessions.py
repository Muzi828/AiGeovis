from __future__ import annotations

import threading
from typing import Dict

sessions: Dict[str, Dict] = {}
parse_progress: Dict[str, Dict] = {}
stop_flags: Dict[str, threading.Event] = {}
