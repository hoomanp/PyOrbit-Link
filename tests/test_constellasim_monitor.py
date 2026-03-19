"""
Unit tests for ConstellaSim AnomalyMonitor (Feature 4).
Tests threshold logic, response parsing, alert deque, and evaluate().
"""
import threading
import pytest
from unittest.mock import MagicMock

from constellasim.monitor import AnomalyMonitor


@pytest.fixture
def mock_ai():
    return MagicMock()


@pytest.fixture
def monitor(mock_ai):
    return AnomalyMonitor(mock_ai)


# ── _thresholds_triggered ─────────────────────────────────────────────────────

class TestThresholdsTrigger:
    def test_high_packet_loss_triggers(self, monitor):
        assert monitor._thresholds_triggered({"packet_loss_pct": 25.0}) is True

    def test_high_latency_triggers(self, monitor):
        assert monitor._thresholds_triggered({"latency_ms": "35.0"}) is True

    def test_failed_status_triggers(self, monitor):
        assert monitor._thresholds_triggered({"status": "Failed"}) is True

    def test_normal_values_no_trigger(self, monitor):
        snap = {"packet_loss_pct": 5.0, "latency_ms": "12.0", "status": "Success"}
        assert monitor._thresholds_triggered(snap) is False

    def test_borderline_packet_loss_no_trigger(self, monitor):
        assert monitor._thresholds_triggered({"packet_loss_pct": 19.9}) is False

    def test_borderline_latency_no_trigger(self, monitor):
        assert monitor._thresholds_triggered({"latency_ms": "29.9"}) is False

    def test_missing_keys_no_crash(self, monitor):
        assert monitor._thresholds_triggered({}) is False

    def test_malformed_latency_no_crash(self, monitor):
        assert monitor._thresholds_triggered({"latency_ms": "N/A"}) is False


# ── _parse_response ───────────────────────────────────────────────────────────

class TestParseResponse:
    def test_warning_parsed(self):
        status, msg = AnomalyMonitor._parse_response(
            "STATUS: WARNING — Packet loss above 20%."
        )
        assert status == "WARNING"
        assert "Packet loss" in msg

    def test_critical_parsed(self):
        status, msg = AnomalyMonitor._parse_response(
            "STATUS: CRITICAL — All routes have dropped; island condition."
        )
        assert status == "CRITICAL"

    def test_nominal_parsed(self):
        status, _ = AnomalyMonitor._parse_response(
            "STATUS: NOMINAL — All metrics nominal."
        )
        assert status == "NOMINAL"

    def test_unknown_on_bad_format(self):
        status, _ = AnomalyMonitor._parse_response("no status here")
        assert status == "UNKNOWN"


# ── get_alerts ────────────────────────────────────────────────────────────────

class TestGetAlerts:
    def test_empty_on_start(self, monitor):
        assert monitor.get_alerts() == []

    def test_returns_list_copy(self, monitor):
        alerts = monitor.get_alerts()
        alerts.append("tamper")
        assert monitor.get_alerts() == []


# ── _evaluate ─────────────────────────────────────────────────────────────────

class TestEvaluate:
    def test_no_data_skips_llm(self, monitor, mock_ai):
        monitor._sim_ref = {}
        monitor._sim_lock = threading.Lock()
        monitor._evaluate()
        mock_ai.chat.assert_not_called()

    def test_normal_metrics_skips_llm(self, monitor, mock_ai):
        monitor._sim_ref = {"packet_loss_pct": 2.0, "latency_ms": "10", "status": "Success"}
        monitor._sim_lock = threading.Lock()
        monitor._evaluate()
        mock_ai.chat.assert_not_called()

    def test_warning_creates_alert(self, monitor, mock_ai):
        mock_ai.chat.return_value = "STATUS: WARNING — High packet loss."
        monitor._sim_ref = {"packet_loss_pct": 30.0}
        monitor._sim_lock = threading.Lock()
        monitor._evaluate()
        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["status"] == "WARNING"

    def test_nominal_creates_no_alert(self, monitor, mock_ai):
        mock_ai.chat.return_value = "STATUS: NOMINAL — All good."
        monitor._sim_ref = {"status": "Failed"}  # triggers threshold
        monitor._sim_lock = threading.Lock()
        monitor._evaluate()
        assert monitor.get_alerts() == []

    def test_llm_error_no_crash(self, monitor, mock_ai):
        mock_ai.chat.side_effect = TimeoutError("LLM timeout")
        monitor._sim_ref = {"packet_loss_pct": 50.0}
        monitor._sim_lock = threading.Lock()
        monitor._evaluate()
        assert monitor.get_alerts() == []

    def test_alert_includes_snapshot(self, monitor, mock_ai):
        mock_ai.chat.return_value = "STATUS: CRITICAL — All routes down."
        snap = {"status": "Failed", "latency_ms": "dropped"}
        monitor._sim_ref = snap
        monitor._sim_lock = threading.Lock()
        monitor._evaluate()
        alert = monitor.get_alerts()[0]
        assert "sim_snapshot" in alert
        assert alert["sim_snapshot"]["status"] == "Failed"

    def test_alerts_capped_at_20(self, mock_ai):
        mock_ai.chat.return_value = "STATUS: WARNING — test."
        mon = AnomalyMonitor(mock_ai)
        mon._sim_ref = {"packet_loss_pct": 99.0}
        mon._sim_lock = threading.Lock()
        for _ in range(30):
            mon._evaluate()
        assert len(mon.get_alerts()) <= 20


# ── Thread-safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_reads_no_crash(self, monitor, mock_ai):
        mock_ai.chat.return_value = "STATUS: WARNING — test."
        monitor._sim_ref = {"packet_loss_pct": 50.0}
        monitor._sim_lock = threading.Lock()
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

        ts = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in ts: t.start()
        for t in ts: t.join(timeout=5)
        assert errors == []
