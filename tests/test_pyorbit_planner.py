"""
Unit tests for PyOrbit-Link MissionPlanner (Feature 3: NL2Function).
Tests JSON extraction, allowlist enforcement, and intent routing.
No real LLM calls — the AI client is fully mocked.
"""
import json
import pytest
from unittest.mock import MagicMock

from pyorbit_link.planner import MissionPlanner, _ALLOWED_FUNCTIONS


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ai():
    return MagicMock()


@pytest.fixture
def planner(mock_ai):
    return MissionPlanner(mock_ai)


# ── _extract_json ──────────────────────────────────────────────────────────────

class TestExtractJson:
    def test_plain_json(self):
        raw = '{"function": "track", "params": {"city": "Tokyo"}}'
        result = MissionPlanner._extract_json(raw)
        assert result["function"] == "track"
        assert result["params"]["city"] == "Tokyo"

    def test_markdown_fenced_json(self):
        raw = '```json\n{"function": "find_events", "params": {"city": "Paris"}}\n```'
        result = MissionPlanner._extract_json(raw)
        assert result["function"] == "find_events"

    def test_markdown_fence_no_lang(self):
        raw = '```\n{"function": "calculate_fspl", "params": {"freq_hz": 2.4e9, "dist_km": 500}}\n```'
        result = MissionPlanner._extract_json(raw)
        assert result["function"] == "calculate_fspl"

    def test_json_embedded_in_prose(self):
        raw = 'Based on your request: {"function": "track", "params": {}} — done.'
        result = MissionPlanner._extract_json(raw)
        assert result["function"] == "track"

    def test_malformed_json_returns_null(self):
        raw = "I cannot parse this at all."
        result = MissionPlanner._extract_json(raw)
        assert result["function"] is None

    def test_empty_string_returns_null(self):
        result = MissionPlanner._extract_json("")
        assert result["function"] is None

    def test_null_function_json(self):
        raw = '{"function": null, "params": {}}'
        result = MissionPlanner._extract_json(raw)
        assert result["function"] is None


# ── Allowlist enforcement ─────────────────────────────────────────────────────

class TestAllowlist:
    def test_all_allowed_functions_present(self):
        assert "track" in _ALLOWED_FUNCTIONS
        assert "find_events" in _ALLOWED_FUNCTIONS
        assert "calculate_fspl" in _ALLOWED_FUNCTIONS

    def test_disallowed_function_name_filtered(self, planner, mock_ai):
        # LLM tries to return an arbitrary/dangerous function name
        mock_ai.chat.return_value = '{"function": "shell_exec", "params": {}}'
        result = planner.parse("do something")
        assert result["function"] is None

    def test_system_import_attempt_filtered(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": "__import__", "params": {}}'
        result = planner.parse("import something")
        assert result["function"] is None

    def test_params_must_be_dict(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": "track", "params": "bad"}'
        result = planner.parse("Track ISS")
        assert result["function"] is None

    def test_params_as_list_filtered(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": "track", "params": [1, 2]}'
        result = planner.parse("Track ISS")
        assert result["function"] is None


# ── parse() happy paths ───────────────────────────────────────────────────────

class TestParse:
    def test_track_intent(self, planner, mock_ai):
        mock_ai.chat.return_value = json.dumps(
            {"function": "track", "params": {"city": "Tokyo"}}
        )
        result = planner.parse("Track ISS over Tokyo")
        assert result["function"] == "track"
        assert result["params"]["city"] == "Tokyo"

    def test_find_events_intent(self, planner, mock_ai):
        mock_ai.chat.return_value = json.dumps(
            {"function": "find_events", "params": {"city": "Paris"}}
        )
        result = planner.parse("When is the next pass over Paris?")
        assert result["function"] == "find_events"

    def test_calculate_fspl_intent(self, planner, mock_ai):
        mock_ai.chat.return_value = json.dumps(
            {"function": "calculate_fspl", "params": {"freq_hz": 12e9, "dist_km": 550.0}}
        )
        result = planner.parse("What is FSPL at 12 GHz and 550 km?")
        assert result["function"] == "calculate_fspl"
        assert result["params"]["freq_hz"] == pytest.approx(12e9)

    def test_unknown_request_returns_null(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": null, "params": {}}'
        result = planner.parse("Order a pizza")
        assert result["function"] is None

    def test_empty_input_skips_llm(self, planner, mock_ai):
        result = planner.parse("")
        mock_ai.chat.assert_not_called()
        assert result["function"] is None

    def test_whitespace_input_skips_llm(self, planner, mock_ai):
        result = planner.parse("   ")
        mock_ai.chat.assert_not_called()
        assert result["function"] is None

    def test_long_input_truncated_to_500(self, planner, mock_ai):
        mock_ai.chat.return_value = '{"function": null, "params": {}}'
        long_input = "x" * 1000
        planner.parse(long_input)
        call_messages = mock_ai.chat.call_args[0][0]
        user_content = next(m["content"] for m in call_messages if m["role"] == "user")
        assert len(user_content) <= 500

    def test_llm_exception_returns_null(self, planner, mock_ai):
        mock_ai.chat.side_effect = RuntimeError("LLM timeout")
        result = planner.parse("Track ISS over London")
        assert result["function"] is None
