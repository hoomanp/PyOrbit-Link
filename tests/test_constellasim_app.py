"""
Integration tests for ConstellaSim Flask API routes.

All external dependencies (LLM, geocoder, network I/O) are mocked.
The SimPy simulation engine runs with real logic — only geocoding and AI are mocked.

Covered endpoints:
  GET  /                      → home page
  POST /api/simulate          → blocking simulation (original)
  GET  /api/simulate/stream   → SSE streaming (Feature 1)
  POST /api/chat              → multi-turn chat (Feature 2)
  POST /api/chat/reset        → clear chat history (Feature 2)
  POST /api/plan              → NL2Function planner (Feature 3)
  GET  /api/alerts            → anomaly alert feed (Feature 4)
  GET  /api/briefing          → markdown network report (Feature 5)
"""
import json
import sys
import os
import importlib.util
import pytest
from unittest.mock import MagicMock, patch

# ── Absolute path to the feature-complete ConstellaSim app ────────────────────
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_APP_PATH = os.path.join(_ROOT, "ConstellaSim", "mobile_client", "app.py")

# ── Mock geocoding map ─────────────────────────────────────────────────────────
_GEO_MAP = {
    "London": (51.5074, -0.1278),
    "New York": (40.7128, -74.0060),
    "Berlin": (52.5200, 13.4050),
}


def _mock_resolve(city):
    return _GEO_MAP.get(city, (None, None))


@pytest.fixture(scope="module")
def constellasim_app():
    """
    Load ConstellaSim/mobile_client/app.py via explicit file path so we
    always get the feature-complete version regardless of sys.path ordering.
    """
    mock_ai = MagicMock()
    mock_ai.analyze_report.return_value = "Mock AI network analysis."
    mock_ai.analyze_report_stream.return_value = iter(["Analysis ", "done."])
    mock_ai.chat.return_value = "Mock chat reply."
    mock_ai.generate_briefing.return_value = "# Network Briefing\n\nMock content.\n"

    mock_planner = MagicMock()
    mock_planner.parse.return_value = {
        "function": "simulate", "params": {"dest_city": "London"}
    }

    mock_geocoder = MagicMock()
    mock_geocoder.resolve_location.side_effect = _mock_resolve

    with patch("constellasim.llm.NetworkAI", return_value=mock_ai), \
         patch("constellasim.utils.Geocoder", return_value=mock_geocoder), \
         patch("constellasim.planner.NetworkPlanner", return_value=mock_planner), \
         patch("constellasim.monitor.AnomalyMonitor"):

        spec = importlib.util.spec_from_file_location("constellasim_mobile_app", _APP_PATH)
        app_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_mod)

    app_mod.ai_analyst = mock_ai
    app_mod._planner = mock_planner
    app_mod._geocoder = mock_geocoder

    app_mod.app.config["TESTING"] = True
    app_mod.app.config["WTF_CSRF_ENABLED"] = False
    return app_mod


@pytest.fixture(scope="module")
def client(constellasim_app):
    with constellasim_app.app.test_client() as c:
        yield c


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestHome:
    def test_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_html_contains_app_title(self, client):
        r = client.get("/")
        assert b"ConstellaSim" in r.data

    def test_contains_sse_eventSource(self, client):
        r = client.get("/")
        assert b"EventSource" in r.data

    def test_contains_chat_endpoint(self, client):
        r = client.get("/")
        assert b"api/chat" in r.data

    def test_contains_briefing_endpoint(self, client):
        r = client.get("/")
        assert b"api/briefing" in r.data


# ── POST /api/simulate ────────────────────────────────────────────────────────

class TestSimulate:
    def test_valid_request_returns_200(self, client):
        r = client.post("/api/simulate",
                        data=json.dumps({"src_lat": 51.5, "src_lon": -0.12, "dest_city": "New York"}),
                        content_type="application/json")
        assert r.status_code == 200

    def test_response_has_latency(self, client):
        r = client.post("/api/simulate",
                        data=json.dumps({"src_lat": 51.5, "src_lon": -0.12, "dest_city": "New York"}),
                        content_type="application/json")
        d = r.get_json()
        assert "latency_ms" in d or d.get("status") == "Failed"

    def test_missing_body_returns_400(self, client):
        r = client.post("/api/simulate", content_type="application/json")
        assert r.status_code == 400

    def test_invalid_latitude_returns_400(self, client):
        r = client.post("/api/simulate",
                        data=json.dumps({"src_lat": 999, "src_lon": 0, "dest_city": "London"}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_invalid_city_returns_400(self, client, constellasim_app):
        constellasim_app._geocoder.resolve_location.side_effect = lambda c: (None, None)
        r = client.post("/api/simulate",
                        data=json.dumps({"src_lat": 51.5, "src_lon": -0.12, "dest_city": "Xyzzy99"}),
                        content_type="application/json")
        # Restore
        constellasim_app._geocoder.resolve_location.side_effect = _mock_resolve
        assert r.status_code in (400, 500)

    def test_updates_last_sim(self, client, constellasim_app):
        client.post("/api/simulate",
                    data=json.dumps({"src_lat": 51.5, "src_lon": -0.12, "dest_city": "New York"}),
                    content_type="application/json")
        with constellasim_app._sim_lock:
            snap = dict(constellasim_app._last_sim)
        assert "status" in snap

    def test_city_too_long_returns_400(self, client):
        r = client.post("/api/simulate",
                        data=json.dumps({"src_lat": 51.5, "src_lon": -0.12, "dest_city": "X" * 200}),
                        content_type="application/json")
        assert r.status_code == 400


# ── GET /api/simulate/stream ──────────────────────────────────────────────────

class TestSimulateStream:
    def test_valid_request_returns_200(self, client):
        r = client.get("/api/simulate/stream?src_lat=51.5&src_lon=-0.12&dest_city=New+York")
        assert r.status_code == 200

    def test_content_type_event_stream(self, client):
        r = client.get("/api/simulate/stream?src_lat=51.5&src_lon=-0.12&dest_city=London")
        assert "text/event-stream" in r.content_type

    def test_contains_simresult_event(self, client):
        r = client.get("/api/simulate/stream?src_lat=51.5&src_lon=-0.12&dest_city=New+York")
        body = r.data.decode()
        assert "event: simresult" in body

    def test_contains_done_event(self, client):
        r = client.get("/api/simulate/stream?src_lat=51.5&src_lon=-0.12&dest_city=New+York")
        assert b"event: done" in r.data

    def test_simresult_has_destination(self, client):
        r = client.get("/api/simulate/stream?src_lat=51.5&src_lon=-0.12&dest_city=New+York")
        body = r.data.decode()
        for line in body.splitlines():
            if line.startswith("data:") and "destination" in line:
                payload = json.loads(line[5:].strip())
                assert "destination" in payload
                break
        else:
            pytest.fail("No simresult data line with destination found")

    def test_missing_src_lat_returns_400(self, client):
        r = client.get("/api/simulate/stream?src_lon=-0.12&dest_city=London")
        assert r.status_code == 400

    def test_out_of_range_lon_returns_400(self, client):
        r = client.get("/api/simulate/stream?src_lat=51.5&src_lon=999&dest_city=London")
        assert r.status_code == 400


# ── POST /api/chat ─────────────────────────────────────────────────────────────

class TestChat:
    def test_valid_message_returns_200(self, client):
        r = client.post("/api/chat",
                        data=json.dumps({"message": "What is the latency?"}),
                        content_type="application/json")
        assert r.status_code == 200

    def test_response_has_reply(self, client):
        r = client.post("/api/chat",
                        data=json.dumps({"message": "Explain packet loss."}),
                        content_type="application/json")
        d = r.get_json()
        assert "reply" in d

    def test_empty_message_returns_400(self, client):
        r = client.post("/api/chat",
                        data=json.dumps({"message": ""}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_missing_body_returns_400(self, client):
        r = client.post("/api/chat", content_type="application/json")
        assert r.status_code == 400

    def test_chat_history_stored_in_session(self, client):
        with client.session_transaction() as sess:
            sess.clear()
        client.post("/api/chat",
                    data=json.dumps({"message": "First question."}),
                    content_type="application/json")
        with client.session_transaction() as sess:
            history = sess.get("chat_history", [])
        assert len(history) >= 2

    def test_history_capped_at_max_turns(self, client, constellasim_app):
        with client.session_transaction() as sess:
            sess.clear()
        for i in range(constellasim_app._MAX_CHAT_TURNS + 5):
            client.post("/api/chat",
                        data=json.dumps({"message": f"msg {i}"}),
                        content_type="application/json")
        with client.session_transaction() as sess:
            history = sess.get("chat_history", [])
        max_expected = 1 + constellasim_app._MAX_CHAT_TURNS * 2
        assert len(history) <= max_expected


# ── POST /api/chat/reset ──────────────────────────────────────────────────────

class TestChatReset:
    def test_returns_200(self, client):
        assert client.post("/api/chat/reset").status_code == 200

    def test_clears_session(self, client):
        client.post("/api/chat",
                    data=json.dumps({"message": "remember me"}),
                    content_type="application/json")
        client.post("/api/chat/reset")
        with client.session_transaction() as sess:
            assert "chat_history" not in sess


# ── POST /api/plan ─────────────────────────────────────────────────────────────

class TestPlan:
    def test_simulate_intent_returns_200(self, client, constellasim_app):
        constellasim_app._planner.parse.return_value = {
            "function": "simulate", "params": {"dest_city": "Berlin"}
        }
        constellasim_app._geocoder.resolve_location.side_effect = _mock_resolve
        r = client.post("/api/plan",
                        data=json.dumps({"query": "Simulate packet to Berlin"}),
                        content_type="application/json")
        assert r.status_code == 200

    def test_topology_info_returns_200(self, client, constellasim_app):
        constellasim_app._planner.parse.return_value = {
            "function": "topology_info", "params": {"sat_count": 5}
        }
        r = client.post("/api/plan",
                        data=json.dumps({"query": "Topology with 5 sats"}),
                        content_type="application/json")
        assert r.status_code == 200

    def test_topology_response_has_sat_count(self, client, constellasim_app):
        constellasim_app._planner.parse.return_value = {
            "function": "topology_info", "params": {"sat_count": 4}
        }
        r = client.post("/api/plan",
                        data=json.dumps({"query": "4 satellites"}),
                        content_type="application/json")
        d = r.get_json()
        assert "sat_count" in d
        assert d["sat_count"] == 4

    def test_null_intent_returns_422(self, client, constellasim_app):
        constellasim_app._planner.parse.return_value = {"function": None, "params": {}}
        r = client.post("/api/plan",
                        data=json.dumps({"query": "random nonsense"}),
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

    def test_sat_count_clamped_to_valid_range(self, client, constellasim_app):
        constellasim_app._planner.parse.return_value = {
            "function": "topology_info", "params": {"sat_count": 9999}
        }
        r = client.post("/api/plan",
                        data=json.dumps({"query": "many sats"}),
                        content_type="application/json")
        d = r.get_json()
        assert d.get("sat_count", 0) <= 20


# ── GET /api/alerts ───────────────────────────────────────────────────────────

class TestAlerts:
    def test_returns_200(self, client):
        assert client.get("/api/alerts").status_code == 200

    def test_returns_json_list(self, client):
        r = client.get("/api/alerts")
        assert isinstance(r.get_json(), list)

    def test_no_monitor_returns_empty_list(self, client, constellasim_app):
        orig = constellasim_app._monitor
        constellasim_app._monitor = None
        r = client.get("/api/alerts")
        assert r.get_json() == []
        constellasim_app._monitor = orig


# ── GET /api/briefing ─────────────────────────────────────────────────────────

class TestBriefing:
    def test_no_sim_data_returns_400(self, client, constellasim_app):
        with constellasim_app._sim_lock:
            constellasim_app._last_sim.clear()
        r = client.get("/api/briefing")
        assert r.status_code == 400

    def test_with_sim_data_returns_200(self, client, constellasim_app):
        with constellasim_app._sim_lock:
            constellasim_app._last_sim.update({
                "status": "Success",
                "latency_ms": "12.3",
                "source": "51.5, -0.12",
                "destination": "New York",
            })
        r = client.get("/api/briefing")
        assert r.status_code == 200

    def test_content_type_is_markdown(self, client, constellasim_app):
        with constellasim_app._sim_lock:
            constellasim_app._last_sim.update({"status": "Success", "latency_ms": "10"})
        r = client.get("/api/briefing")
        assert "text/markdown" in r.content_type

    def test_attachment_disposition(self, client, constellasim_app):
        with constellasim_app._sim_lock:
            constellasim_app._last_sim.update({"status": "Success"})
        r = client.get("/api/briefing")
        cd = r.headers.get("Content-Disposition", "")
        assert "attachment" in cd
        assert "network_briefing.md" in cd

    def test_body_contains_briefing_content(self, client, constellasim_app):
        with constellasim_app._sim_lock:
            constellasim_app._last_sim.update({"status": "Success"})
        r = client.get("/api/briefing")
        assert b"Network Briefing" in r.data
