"""
Integration tests for PyOrbit-Link Flask API routes.

All external dependencies (LLM, satellite tracker, TLE fetching) are mocked.
Tests run against Flask's test client — no real network calls.

Covered endpoints:
  GET  /                   → home page
  POST /api/track          → telemetry (blocking)
  GET  /api/track/stream   → SSE streaming (Feature 1)
  POST /api/chat           → multi-turn chat (Feature 2)
  POST /api/chat/reset     → clear chat history (Feature 2)
  POST /api/plan           → NL2Function planner (Feature 3)
  GET  /api/alerts         → anomaly alert feed (Feature 4)
  GET  /api/briefing       → markdown mission report (Feature 5)
"""
import json
import sys
import os
import importlib.util
import pytest
from unittest.mock import MagicMock, patch

from tests.conftest import MOCK_TLE

# ── Absolute path to the feature-complete PyOrbit-Link app ───────────────────
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP_PATH = os.path.join(_ROOT, "PyOrbit-Link", "mobile_client", "app.py")


# ── App fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pyorbit_app():
    """
    Load PyOrbit-Link/mobile_client/app.py via explicit file path so we
    always get the feature-complete version regardless of sys.path ordering.
    External dependencies (CelesTrakAPI, MissionAI) are mocked.
    """
    mock_ai = MagicMock()
    mock_ai.get_analysis.return_value = "Mock AI analysis."
    mock_ai.get_analysis_stream.return_value = iter(["Analysis ", "complete."])
    mock_ai.chat.return_value = "Mock chat reply."
    mock_ai.generate_briefing.return_value = "# Mission Briefing\n\nMock content.\n"

    mock_planner = MagicMock()
    mock_planner.parse.return_value = {"function": "track", "params": {"city": "London"}}

    mock_loc_instance = MagicMock()
    mock_loc_instance.get_lat_lon.return_value = (51.5, -0.12, "London, UK")

    mock_tracker = MagicMock()
    mock_tracker.get_aer.return_value = (180.0, 45.0, 420.0)   # az_deg, el_deg, dist_km
    mock_tracker.find_events.return_value = [
        {"Rise": "2024-01-01T12:00:00Z", "Culmination": "2024-01-01T12:05:00Z", "Set": "2024-01-01T12:10:00Z"}
    ]

    with patch("pyorbit_link.api.CelesTrakAPI.get_tle_by_norad_id", return_value=MOCK_TLE), \
         patch("pyorbit_link.llm.MissionAI", return_value=mock_ai), \
         patch("pyorbit_link.utils.LocationProvider", return_value=mock_loc_instance), \
         patch("pyorbit_link.planner.MissionPlanner", return_value=mock_planner), \
         patch("pyorbit_link.monitor.AnomalyMonitor"), \
         patch("pyorbit_link.tracker.SatTracker", return_value=mock_tracker):

        spec = importlib.util.spec_from_file_location("pyorbit_mobile_app", _APP_PATH)
        app_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_mod)

    # After load, override all module-level globals with controllable mocks
    app_mod.ai_assistant = mock_ai
    app_mod._planner = mock_planner
    app_mod._location_provider = mock_loc_instance
    app_mod._tracker = mock_tracker
    app_mod.TLE_CACHE = MOCK_TLE

    app_mod.app.config["TESTING"] = True
    app_mod.app.config["WTF_CSRF_ENABLED"] = False
    return app_mod


@pytest.fixture(scope="module")
def client(pyorbit_app):
    with pyorbit_app.app.test_client() as c:
        yield c


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestHome:
    def test_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_html_content(self, client):
        r = client.get("/")
        assert b"PyOrbit-Link" in r.data

    def test_contains_sse_eventSource(self, client):
        r = client.get("/")
        assert b"EventSource" in r.data

    def test_contains_chat_widget(self, client):
        r = client.get("/")
        assert b"api/chat" in r.data

    def test_contains_briefing_button(self, client):
        r = client.get("/")
        assert b"api/briefing" in r.data


# ── POST /api/track ───────────────────────────────────────────────────────────

class TestTrack:
    def test_valid_coords_returns_200(self, client):
        r = client.post("/api/track",
                        data=json.dumps({"latitude": 51.5, "longitude": -0.12}),
                        content_type="application/json")
        assert r.status_code == 200

    def test_response_has_required_keys(self, client):
        r = client.post("/api/track",
                        data=json.dumps({"latitude": 35.6, "longitude": 139.7}),
                        content_type="application/json")
        d = r.get_json()
        for key in ("sat_name", "azimuth", "elevation", "distance", "fspl_db", "ai_analysis"):
            assert key in d, f"missing key: {key}"

    def test_missing_body_returns_400(self, client):
        r = client.post("/api/track", content_type="application/json")
        assert r.status_code == 400

    def test_invalid_latitude_returns_400(self, client):
        r = client.post("/api/track",
                        data=json.dumps({"latitude": 999, "longitude": 0}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_invalid_longitude_returns_400(self, client):
        r = client.post("/api/track",
                        data=json.dumps({"latitude": 0, "longitude": 999}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_string_coords_return_400(self, client):
        r = client.post("/api/track",
                        data=json.dumps({"latitude": "abc", "longitude": 0}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_updates_last_telemetry(self, client, pyorbit_app):
        client.post("/api/track",
                    data=json.dumps({"latitude": 48.8, "longitude": 2.3}),
                    content_type="application/json")
        with pyorbit_app._telemetry_lock:
            snap = dict(pyorbit_app._last_telemetry)
        assert "elevation" in snap
        assert snap["observer_lat"] == pytest.approx(48.8)


# ── GET /api/track/stream ─────────────────────────────────────────────────────

class TestTrackStream:
    def test_valid_coords_returns_200(self, client):
        r = client.get("/api/track/stream?lat=51.5&lon=-0.12")
        assert r.status_code == 200

    def test_content_type_is_event_stream(self, client):
        r = client.get("/api/track/stream?lat=51.5&lon=-0.12")
        assert "text/event-stream" in r.content_type

    def test_response_contains_telemetry_event(self, client):
        r = client.get("/api/track/stream?lat=51.5&lon=-0.12")
        body = r.data.decode()
        assert "event: telemetry" in body

    def test_response_contains_done_event(self, client):
        r = client.get("/api/track/stream?lat=51.5&lon=-0.12")
        body = r.data.decode()
        assert "event: done" in body

    def test_telemetry_event_has_sat_name(self, client):
        r = client.get("/api/track/stream?lat=51.5&lon=-0.12")
        body = r.data.decode()
        # Find the telemetry event data line
        for line in body.splitlines():
            if line.startswith("data:") and "sat_name" in line:
                payload = json.loads(line[len("data:"):].strip())
                assert "sat_name" in payload
                break
        else:
            pytest.fail("No telemetry data line found with sat_name")

    def test_missing_lat_returns_400(self, client):
        r = client.get("/api/track/stream?lon=-0.12")
        assert r.status_code == 400

    def test_missing_lon_returns_400(self, client):
        r = client.get("/api/track/stream?lat=51.5")
        assert r.status_code == 400

    def test_out_of_range_lat_returns_400(self, client):
        r = client.get("/api/track/stream?lat=200&lon=0")
        assert r.status_code == 400

    def test_ai_tokens_streamed_as_data_lines(self, client, pyorbit_app):
        pyorbit_app.ai_assistant.get_analysis_stream.return_value = iter(["tok1", " tok2"])
        r = client.get("/api/track/stream?lat=51.5&lon=-0.12")
        body = r.data.decode()
        data_lines = [l for l in body.splitlines() if l.startswith("data:")]
        # Should have at least: telemetry (skip - that's event:), tokens, done
        token_lines = [l for l in data_lines if "tok" in l or "tok" in json.loads(l[5:].strip())]
        assert len(token_lines) >= 1


# ── POST /api/chat ─────────────────────────────────────────────────────────────

class TestChat:
    def test_valid_message_returns_200(self, client):
        r = client.post("/api/chat",
                        data=json.dumps({"message": "What is FSPL?"}),
                        content_type="application/json")
        assert r.status_code == 200

    def test_response_has_reply_key(self, client):
        r = client.post("/api/chat",
                        data=json.dumps({"message": "Explain elevation."}),
                        content_type="application/json")
        d = r.get_json()
        assert "reply" in d
        assert d["reply"] == "Mock chat reply."

    def test_missing_body_returns_400(self, client):
        r = client.post("/api/chat", content_type="application/json")
        assert r.status_code == 400

    def test_empty_message_returns_400(self, client):
        r = client.post("/api/chat",
                        data=json.dumps({"message": ""}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_whitespace_message_returns_400(self, client):
        r = client.post("/api/chat",
                        data=json.dumps({"message": "   "}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_history_stored_in_session(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        client.post("/api/chat",
                    data=json.dumps({"message": "First message."}),
                    content_type="application/json")
        with client.session_transaction() as sess:
            history = sess.get("chat_history", [])
        assert len(history) >= 2  # system + user + assistant

    def test_history_capped_at_max_turns(self, client, pyorbit_app):
        """After MAX_CHAT_TURNS exchanges, history doesn't grow unboundedly."""
        with client.session_transaction() as sess:
            sess.clear()
        for i in range(pyorbit_app._MAX_CHAT_TURNS + 5):
            client.post("/api/chat",
                        data=json.dumps({"message": f"msg {i}"}),
                        content_type="application/json")
        with client.session_transaction() as sess:
            history = sess.get("chat_history", [])
        max_expected = 1 + pyorbit_app._MAX_CHAT_TURNS * 2
        assert len(history) <= max_expected


# ── POST /api/chat/reset ──────────────────────────────────────────────────────

class TestChatReset:
    def test_returns_200(self, client):
        r = client.post("/api/chat/reset")
        assert r.status_code == 200

    def test_clears_session_history(self, client):
        client.post("/api/chat",
                    data=json.dumps({"message": "remember this"}),
                    content_type="application/json")
        client.post("/api/chat/reset")
        with client.session_transaction() as sess:
            assert "chat_history" not in sess


# ── POST /api/plan ─────────────────────────────────────────────────────────────

class TestPlan:
    def test_valid_query_track_returns_200(self, client, pyorbit_app):
        pyorbit_app._planner.parse.return_value = {
            "function": "track", "params": {"city": "London"}
        }
        r = client.post("/api/plan",
                        data=json.dumps({"query": "Track ISS over London"}),
                        content_type="application/json")
        assert r.status_code == 200

    def test_track_response_has_telemetry_keys(self, client, pyorbit_app):
        pyorbit_app._planner.parse.return_value = {
            "function": "track", "params": {"city": "London"}
        }
        r = client.post("/api/plan",
                        data=json.dumps({"query": "Track ISS over London"}),
                        content_type="application/json")
        d = r.get_json()
        assert "sat_name" in d or "azimuth" in d

    def test_calculate_fspl_returns_fspl_db(self, client, pyorbit_app):
        pyorbit_app._planner.parse.return_value = {
            "function": "calculate_fspl",
            "params": {"freq_hz": 2.4e9, "dist_km": 400.0}
        }
        r = client.post("/api/plan",
                        data=json.dumps({"query": "FSPL at 2.4 GHz 400 km"}),
                        content_type="application/json")
        d = r.get_json()
        assert "fspl_db" in d

    def test_unknown_intent_returns_422(self, client, pyorbit_app):
        pyorbit_app._planner.parse.return_value = {"function": None, "params": {}}
        r = client.post("/api/plan",
                        data=json.dumps({"query": "Order a pizza"}),
                        content_type="application/json")
        assert r.status_code == 422

    def test_empty_query_returns_400(self, client):
        r = client.post("/api/plan",
                        data=json.dumps({"query": ""}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_missing_body_returns_400(self, client):
        r = client.post("/api/plan", content_type="application/json")
        assert r.status_code == 400

    def test_negative_fspl_params_returns_400(self, client, pyorbit_app):
        pyorbit_app._planner.parse.return_value = {
            "function": "calculate_fspl",
            "params": {"freq_hz": -1, "dist_km": 400.0}
        }
        r = client.post("/api/plan",
                        data=json.dumps({"query": "FSPL at -1 Hz"}),
                        content_type="application/json")
        assert r.status_code == 400


# ── GET /api/alerts ───────────────────────────────────────────────────────────

class TestAlerts:
    def test_returns_200(self, client):
        r = client.get("/api/alerts")
        assert r.status_code == 200

    def test_returns_list(self, client):
        r = client.get("/api/alerts")
        assert isinstance(r.get_json(), list)

    def test_no_monitor_returns_empty_list(self, client, pyorbit_app):
        original = pyorbit_app._monitor
        pyorbit_app._monitor = None
        r = client.get("/api/alerts")
        assert r.get_json() == []
        pyorbit_app._monitor = original


# ── GET /api/briefing ─────────────────────────────────────────────────────────

class TestBriefing:
    def test_no_telemetry_returns_400(self, client, pyorbit_app):
        with pyorbit_app._telemetry_lock:
            pyorbit_app._last_telemetry.clear()
        r = client.get("/api/briefing")
        assert r.status_code == 400

    def test_with_telemetry_returns_200(self, client, pyorbit_app):
        with pyorbit_app._telemetry_lock:
            pyorbit_app._last_telemetry.update({
                "elevation": "45°", "azimuth": "180°",
                "distance": "420 km", "fspl_db": "155 dB"
            })
        r = client.get("/api/briefing")
        assert r.status_code == 200

    def test_response_is_markdown_content_type(self, client, pyorbit_app):
        with pyorbit_app._telemetry_lock:
            pyorbit_app._last_telemetry.update({"elevation": "30°"})
        r = client.get("/api/briefing")
        assert "text/markdown" in r.content_type

    def test_response_has_attachment_disposition(self, client, pyorbit_app):
        with pyorbit_app._telemetry_lock:
            pyorbit_app._last_telemetry.update({"elevation": "30°"})
        r = client.get("/api/briefing")
        assert "attachment" in r.headers.get("Content-Disposition", "")
        assert "mission_briefing.md" in r.headers.get("Content-Disposition", "")

    def test_response_body_is_markdown(self, client, pyorbit_app):
        with pyorbit_app._telemetry_lock:
            pyorbit_app._last_telemetry.update({"elevation": "30°"})
        r = client.get("/api/briefing")
        assert b"Mission Briefing" in r.data
