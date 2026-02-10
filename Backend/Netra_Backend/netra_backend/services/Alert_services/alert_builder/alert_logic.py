import json
from typing import Dict, Any, List, Optional
import sys
sys.stdout.reconfigure(line_buffering=True)


def load_alert_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_config_index(config: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    index = {}
    for pkt in config.get("packets", []):
        if isinstance(pkt, dict) and isinstance(pkt.get("queue_id"), int):
            index[pkt["queue_id"]] = pkt
    return index


def evaluate_metric(
    metric: str,
    value: float,
    min_v: Optional[float],
    max_v: Optional[float],
    thresholds: Dict[str, int]
):
    # ---------- HARD RED ----------
    if min_v is not None and value < min_v:
        return "RED", 100, "Value below minimum limit"

    if max_v is not None and value > max_v:
        return "RED", 100, "Value above maximum limit"

    if min_v is None or max_v is None or max_v == min_v:
        return None

    # ---------- PERCENTAGE PROXIMITY ----------
    range_v = max_v - min_v
    distance_to_limit = min(value - min_v, max_v - value)
    percent_used = round(100 * (1 - distance_to_limit / range_v), 2)

    if percent_used >= thresholds["red_percent"]:
        return "RED", percent_used, "Reached 100% operational limit"

    if percent_used >= thresholds["amber_percent"]:
        return "AMBER", percent_used, "Above 90% operational limit"

    if percent_used >= thresholds["yellow_percent"]:
        return "YELLOW", percent_used, "Above 80% operational limit"

    return None


def evaluate_tm(
    tm_message: Dict[str, Any],
    config_index: Dict[int, Dict[str, Any]],
    thresholds: Dict[str, int],
    submodule_index: Dict[str, str] = None
) -> List[Dict[str, Any]]:
    print(tm_message)
    alerts: List[Dict[str, Any]] = []

    submodule_index = submodule_index or {}

    meta = tm_message.get("meta", {})
    timestamp = meta.get("timestamp")
    raw_packet_name = meta.get("packet_name", "UNKNOWN")

    for inst in tm_message.get("data", []):
        raw_queue_id = inst.get("Queue_ID")
        raw_submodule_id = str(inst.get("Submodule_ID"))
        
        # Resolve Submodule Name
        submodule_name = submodule_index.get(raw_submodule_id, f"Submodule_{raw_submodule_id}")

        try:
            queue_id = int(raw_queue_id)
        except (ValueError, TypeError):
            continue

        if queue_id not in config_index:
            continue

        packet_cfg = config_index[queue_id]
        matched_packet_name = packet_cfg.get("packet_name", "UNKNOWN")
        
        # Hierarchical Threshold Check: Local (Packet) overrides Global
        active_thresholds = packet_cfg.get("thresholds", thresholds)

        for metric, limits in packet_cfg.get("metrics", {}).items():
            if metric not in inst:
                continue

            value = inst[metric]
            min_v = limits.get("min")
            max_v = limits.get("max")

            result = evaluate_metric(metric, value, min_v, max_v, active_thresholds)
            if not result:
                continue

            severity, percent, reason = result

            alerts.append({
                "timestamp": timestamp,
                "raw_packet_name": raw_packet_name,
                "matched_packet_name": matched_packet_name,
                "submodule_id": raw_submodule_id,
                "submodule_name": submodule_name,
                "queue_id": queue_id,
                "metric": metric,
                "value": value,
                "min": min_v,
                "max": max_v,
                "severity": severity,
                "severity_percent": percent,
                "reason": reason,
                "status": "alert_identified"
            })

    return alerts
