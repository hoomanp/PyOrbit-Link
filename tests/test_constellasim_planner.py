"""
Unit tests for ConstellaSim NetworkPlanner (Feature 3: NL2Function).
"""
import json
import pytest
from unittest.mock import MagicMock

from constellasim.planner import NetworkPlanner, _ALLOWED_FUNCTIONS


@pytest.fixture
def mock_ai():
    return MagicMock()


@pytest.fixture
def planner(mock_ai):
    return NetworkPlanner(mock_ai)


# ── _extract_json ──────────────────────────────────────────────────────────────

class TestExtractJson:
    def test_plain_json(self):
        raw = '{"function": "simulate", "params": {"dest_city": "Berlin"}}'
        result = NetworkPlanner._extract_json(raw)
        assert result["function"] == "simulate"

    def test_markdown_fenced(self):
        raw = '```json\n{"function": "topology_info", "params": {"sat_count": 6}}\n```'
        result = NetworkPlanner._extract_json(raw)
        assert result["function"] == "topology_info"
        assert result["params"]["sat_count"] == 6

    def test_null_function(self):
        raw = '{"function": null, "params": {}}'
        result = NetworkPlanner._extract_json(raw)
        assert result["function"] is None

    def test_invalid_json(self):
        result = NetworkPlanner._extract_json("not json at all")
        assert result["function"] is None


# ── Allowlist ─────────────────────────────────────────────────────────────────

class TestAllowlist:
    def test_allowed_functions_correct(self):
        assert "simulate" in _ALLOWED_FUNCTIONS
        assert "topology_info" in _ALLOWED_FUNCTIONS

    def test_arbitrary_function_blocked(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": "delete_all", "params": {}}'
        result = planner.parse("delete everything")
        assert result["function"] is None

    def test_params_as_string_blocked(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": "simulate", "params": "oops"}'
        result = planner.parse("simulate")
        assert result["function"] is None


# ── parse() ───────────────────────────────────────────────────────────────────

class TestParse:
    def test_simulate_intent(self, planner, mock_ai):
        mock_ai.chat.return_value = json.dumps(
            {"function": "simulate", "params": {"dest_city": "Tokyo"}}
        )
        result = planner.parse("Simulate a packet to Tokyo")
        assert result["function"] == "simulate"
        assert result["params"]["dest_city"] == "Tokyo"

    def test_topology_info_intent(self, planner, mock_ai):
        mock_ai.chat.return_value = json.dumps(
            {"function": "topology_info", "params": {"sat_count": 6}}
        )
        result = planner.parse("How does the topology look with 6 satellites?")
        assert result["function"] == "topology_info"
        assert result["params"]["sat_count"] == 6

    def test_empty_query_skips_llm(self, planner, mock_ai):
        result = planner.parse("")
        mock_ai.chat.assert_not_called()
        assert result["function"] is None

    def test_llm_failure_returns_null(self, planner, mock_ai):
        mock_ai.chat.side_effect = ConnectionError("LLM offline")
        result = planner.parse("simulate packet to Berlin")
        assert result["function"] is None

    def test_query_truncated_to_500_chars(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": null, "params": {}}'
        planner.parse("q" * 1000)
        messages = mock_ai.chat.call_args[0][0]
        user_msg = next(m for m in messages if m["role"] == "user")
        assert len(user_msg["content"]) <= 500

    def test_null_from_llm_returns_null(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": null, "params": {}}'
        result = planner.parse("make me a sandwich")
        assert result["function"] is None
