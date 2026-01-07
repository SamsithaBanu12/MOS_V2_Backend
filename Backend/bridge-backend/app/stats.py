# app/stats.py
from __future__ import annotations
from typing import Dict, Tuple, Optional
import threading

# The four logical topics used across the app (not raw MQTT topics)
LOGICAL_TOPICS = (
    "cosmos/command",
    "cosmos/telemetry",
    "SatOS/uplink",
    "SatOS/downlink",
)

def _zero():
    return {"rx_msgs": 0, "rx_bytes": 0, "tx_msgs": 0, "tx_bytes": 0}

class Stats:
    """
    Station-aware counters.
    counters[(station_id, logical_topic)] = { rx_msgs, rx_bytes, tx_msgs, tx_bytes }
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.counters: Dict[Tuple[str, str], Dict[str, int]] = {}

    def _ensure(self, station_id: str, topic: str) -> Dict[str, int]:
        return self.counters.setdefault((station_id, topic), _zero())

    def bump(self, station_id: str, topic: str, direction: str, byte_cnt: int) -> None:
        if topic not in LOGICAL_TOPICS:
            # Ignore unexpected logical topics to keep data consistent
            return
        with self._lock:
            c = self._ensure(station_id, topic)
            if direction == "rx":
                c["rx_msgs"] += 1
                c["rx_bytes"] += int(byte_cnt)
            else:
                c["tx_msgs"] += 1
                c["tx_bytes"] += int(byte_cnt)

    def snapshot(self, station_id: Optional[str] = None):
        """
        If station_id is provided, returns { topic: counters } for that station,
        always including all LOGICAL_TOPICS with zeroed counters if unused.

        If station_id is None, returns { station_id: { topic: counters } } for all
        stations discovered so far, again materializing all LOGICAL_TOPICS.
        """
        with self._lock:
            if station_id is not None:
                out: Dict[str, Dict[str, int]] = {}
                for t in LOGICAL_TOPICS:
                    out[t] = dict(self.counters.get((station_id, t), _zero()))
                return out

            # All stations seen so far
            stations = {sid for (sid, _t) in self.counters.keys()}
            res: Dict[str, Dict[str, Dict[str, int]]] = {}
            for sid in stations:
                tmp: Dict[str, Dict[str, int]] = {}
                for t in LOGICAL_TOPICS:
                    tmp[t] = dict(self.counters.get((sid, t), _zero()))
                res[sid] = tmp
            return res
