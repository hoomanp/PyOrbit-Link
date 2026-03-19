"""
Unit tests for PyOrbit-Link AnomalyMonitor (Feature 4).
Tests threshold logic, LLM response parsing, alert storage,
and evaluate() integration — no real LLM calls.
"""
import time
import threading
import pytest
from unittest.mock import MagicMock

from pyorbit_link.monitor import AnomalyMonitor


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ai():
    return MagicMock()


@pytest.fixture
def monitor(mock_ai):
    return AnomalyMonitor(mock_ai)


# ── _thresholds_triggered ─────────────────────────────────────────────────────

class TestThresholdsTrigger:
    def test_low_elevation_triggers(self, monitor):
        assert monitor._thresholds_triggered({"elevation": "10.00°"}) is True

    def test_zero_elevation_triggers(self, monitor):
        assert monitor._thresholds_triggered({"elevation": "0.00°"}) is True

    def test_borderline_elevation_above_threshold_no_trigger(self, monitor):
        # 15° is the threshold; 15.5° should NOT trigger
        assert monitor._thresholds_triggered({"elevation": "15.50°"}) is False

    def test_high_fspl_triggers(self, monitor):
        assert monitor._thresholds_triggered({"fspl_db": "165.00 dB"}) is True

    def test_borderline_fspl_below_threshold_no_trigger(self, monitor):
        assert monitor._thresholds_triggered({"fspl_db": "159.99 dB"}) is False

    def test_normal_values_no_trigger(self, monitor):
        snap = {"elevation": "45.00°", "fspl_db": "155.00 dB"}
        assert monitor._thresholds_triggered(snap) is False

    def test_missing_elevation_no_crash(self, monitor):
        assert monitor._thresholds_triggered({"fspl_db": "100.00 dB"}) is False

    def test_malformed_elevation_no_crash(self, monitor):
        assert monitor._thresholds_triggered({"elevation": "N/A"}) is False


# ── _parse_response ───────────────────────────────────────────────────────────

class TestParseResponse:
    def test_parses_warning(self):
        text = "STATUS: WARNING — Elevation below safe threshold for reliable comms."
        status, msg = AnomalyMonitor._parse_response(text)
        assert status == "WARNING"
        assert "Elevation" in msg

    def test_parses_critical(self):
        text = "STATUS: CRITICAL — Link margin is negative; connection will drop."
        status, msg = AnomalyMonitor._parse_response(text)
        assert status == "CRITICAL"

    def test_parses_nominal(self):
        text = "STATUS: NOMINAL — All metrics within acceptable bounds."
        status, msg = AnomalyMonitor._parse_response(text)
        assert status == "NOMINAL"

    def test_malformed_response_returns_unknown(self):
        text = "I don't know how to classify this."
        status, msg = AnomalyMonitor._parse_response(text)
        assert status == "UNKNOWN"

    def test_multiline_response_finds_status_line(self):
        text = "Some preamble.\nSTATUS: WARNING — High FSPL detected.\nMore text."
        status, _ = AnomalyMonitor._parse_response(text)
        assert status == "WARNING"


# ── get_alerts ────────────────────────────────────────────────────────────────

class TestGetAlerts:
    def test_initially_empty(self, monitor):
        assert monitor.get_alerts() == []

    def test_returns_copy_not_reference(self, monitor):
        alerts = monitor.get_alerts()
        alerts.append("tamper")
        assert monitor.get_alerts() == []


# ── _evaluate integration ─────────────────────────────────────────────────────

class TestEvaluate:
    def test_no_telemetry_skips_llm(self, monitor, mock_ai):
        monitor._telemetry_ref = {}
        monitor._telemetry_lock = threading.Lock()
        monitor._evaluate()
        mock_ai.chat.assert_not_called()

    def test_normal_values_skips_llm(self, monitor, mock_ai):
        monitor._telemetry_ref = {"elevation": "45°", "fspl_db": "150 dB"}
        monitor._telemetry_lock = threading.Lock()
        monitor._evaluate()
        mock_ai.chat.assert_not_called()

    def test_warning_creates_alert(self, monitor, mock_ai):
        mock_ai.chat.return_value = "STATUS: WARNING — Elevation below threshold."
        monitor._telemetry_ref = {"elevation": "5.00°"}
        monitor._telemetry_lock = threading.Lock()
        monitor._evaluate()
        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["status"] == "WARNING"
        assert "Elevation" in alerts[0]["message"]

    def test_critical_creates_alert(self, monitor, mock_ai):
        mock_ai.chat.return_value = "STATUS: CRITICAL — Link completely lost."
        monitor._telemetry_ref = {"fspl_db": "170.00 dB"}
        monitor._telemetry_lock = threading.Lock()
        monitor._evaluate()
        alerts = monitor.get_alerts()
        assert any(a["status"] == "CRITICAL" for a in alerts)

    def test_nominal_does_not_create_alert(self, monitor, mock_ai):
        mock_ai.chat.return_value = "STATUS: NOMINAL — All good."
        monitor._telemetry_ref = {"elevation": "5.00°"}  # triggers threshold check
        monitor._telemetry_lock = threading.Lock()
        monitor._evaluate()
        # NOMINAL should NOT add to alerts
        assert all(a["status"] != "NOMINAL" for a in monitor.get_alerts())

    def test_llm_failure_no_crash(self, monitor, mock_ai):
        mock_ai.chat.side_effect = RuntimeError("timeout")
        monitor._telemetry_ref = {"elevation": "5.00°"}
        monitor._telemetry_lock = threading.Lock()
        monitor._evaluate()  # must not raise
        assert monitor.get_alerts() == []

    def test_alerts_capped_at_20(self, mock_ai):
        """deque(maxlen=20) — oldest alert is evicted when full."""
        mock_ai.chat.return_value = "STATUS: WARNING — test."
        mon = AnomalyMonitor(mock_ai)
        mon._telemetry_ref = {"elevation": "5.00°"}
        mon._telemetry_lock = threading.Lock()
        for _ in range(25):
            mon._evaluate()
        assert len(mon.get_alerts()) <= 20


# ── Thread-safety smoke test ───────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_get_alerts_no_crash(self, monitor, mock_ai):
        mock_ai.chat.return_value = "STATUS: WARNING — test."
        monitor._telemetry_ref = {"elevation": "5.00°"}
        monitor._telemetry_lock = threading.Lock()

        errors = []

        def writer():
            try:
                for _ in range(10):
                    monitor._evaluate()
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(20):
                    monitor.get_alerts()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == []
