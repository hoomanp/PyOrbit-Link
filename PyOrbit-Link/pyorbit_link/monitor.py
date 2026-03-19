"""Feature 4: AI Anomaly Monitor for PyOrbit-Link.

Runs a background daemon thread that periodically evaluates the latest telemetry
snapshot and writes anomaly alerts to an in-memory deque. Enable with:

    ANOMALY_MONITOR=true

in the environment.
"""

import json
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Thresholds for triggering anomaly evaluation
_ELEVATION_LOW_DEG = 15.0
_FSPL_HIGH_DB = 160.0
_CNR_LOW_DB = 6.0

_MONITOR_INTERVAL_SECONDS = 30

_SHORT_PROMPT = (
    "You are a satellite link monitor. Given the following telemetry metrics, "
    "classify the overall link health as NOMINAL, WARNING, or CRITICAL "
    "and explain why in exactly one sentence.\n\n"
    "Metrics: {metrics}\n\n"
    "Respond in this exact format:\n"
    "STATUS: <NOMINAL|WARNING|CRITICAL> — <one-sentence explanation>"
)


class AnomalyMonitor:
    """Background thread that evaluates telemetry and emits timestamped alerts."""

    def __init__(self, ai_client):
        self._ai = ai_client
        self._alerts = deque(maxlen=20)
        self._lock = threading.Lock()
        self._telemetry_ref = None  # set by set_telemetry_source()
        self._telemetry_lock = None
        self._running = False
        self._thread = None

    def set_telemetry_source(self, telemetry_dict, telemetry_lock):
        """Register the module-level telemetry dict and its lock."""
        self._telemetry_ref = telemetry_dict
        self._telemetry_lock = telemetry_lock

    def start(self):
        """Start the background monitoring thread (daemon=True)."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="AnomalyMonitor")
        self._thread.start()
        logger.info("AnomalyMonitor started")

    def get_alerts(self):
        """Return a snapshot of current alerts as a list (newest first)."""
        with self._lock:
            return list(reversed(self._alerts))

    def _run(self):
        while self._running:
            try:
                self._evaluate()
            except Exception:
                logger.exception("AnomalyMonitor evaluation error")
            time.sleep(_MONITOR_INTERVAL_SECONDS)

    def _evaluate(self):
        if self._telemetry_ref is None or self._telemetry_lock is None:
            return

        with self._telemetry_lock:
            snapshot = dict(self._telemetry_ref)

        if not snapshot:
            return  # no data yet

        # Check thresholds to decide whether to call LLM at all
        should_check = self._thresholds_triggered(snapshot)
        if not should_check:
            return

        metrics_str = json.dumps(snapshot)
        prompt_text = _SHORT_PROMPT.format(metrics=metrics_str)

        try:
            messages = [{"role": "user", "content": prompt_text}]
            response = self._ai.chat(messages)
        except Exception:
            logger.exception("AnomalyMonitor LLM call failed")
            return

        status, explanation = self._parse_response(response)
        if status in ("WARNING", "CRITICAL"):
            alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "message": explanation,
                "telemetry": snapshot,
            }
            with self._lock:
                self._alerts.append(alert)
            logger.warning("Anomaly detected: %s — %s", status, explanation)

    def _thresholds_triggered(self, snapshot):
        """Return True if any metric exceeds a threshold warranting LLM evaluation."""
        try:
            el = float(str(snapshot.get("elevation", "90")).replace("°", ""))
            if el < _ELEVATION_LOW_DEG:
                return True
        except (ValueError, TypeError):
            pass
        try:
            fspl = float(str(snapshot.get("fspl_db", "0")).replace(" dB", ""))
            if fspl > _FSPL_HIGH_DB:
                return True
        except (ValueError, TypeError):
            pass
        return False

    @staticmethod
    def _parse_response(text):
        """Extract STATUS and explanation from the LLM response."""
        for line in text.splitlines():
            if line.startswith("STATUS:"):
                parts = line[len("STATUS:"):].strip().split("—", 1)
                status = parts[0].strip().upper()
                explanation = parts[1].strip() if len(parts) > 1 else line
                return status, explanation
        return "UNKNOWN", text.strip()
