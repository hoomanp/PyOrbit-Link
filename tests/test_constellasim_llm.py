"""
Unit tests for ConstellaSim NetworkAI new methods:
  - Feature 1: analyze_report_stream() + provider stream helpers
  - Feature 2: chat() + _chat_google() message-format conversion
  - Feature 5: generate_briefing()
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from constellasim.llm import NetworkAI


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_ai(provider="google"):
    with patch.object(NetworkAI, "_init_clients"), \
         patch.object(NetworkAI, "_load_kb", return_value="mock KB context"):
        ai = NetworkAI(provider=provider)
    return ai


def _gemini_stream_chunks(texts):
    return [MagicMock(text=t) for t in texts]


def _azure_stream_chunks(texts):
    chunks = []
    for t in texts:
        delta = MagicMock(); delta.content = t
        choice = MagicMock(); choice.delta = delta
        chunk = MagicMock(); chunk.choices = [choice]
        chunks.append(chunk)
    return chunks


def _bedrock_events(texts):
    return [
        {"chunk": {"bytes": json.dumps({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": t}
        }).encode()}}
        for t in texts
    ]


# ── Feature 1: analyze_report_stream ─────────────────────────────────────────

class TestAnalyzeReportStream:
    def test_google_yields_chunks(self):
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        ai._google_model.generate_content.return_value = _gemini_stream_chunks(["Lat ", "good"])
        result = list(ai.analyze_report_stream("--- ConstellaSim Report ---\nLatency: 10ms"))
        assert result == ["Lat ", "good"]

    def test_azure_yields_chunks(self):
        ai = _make_ai("azure")
        ai._azure_client = MagicMock()
        ai._azure_client.chat.completions.create.return_value = iter(
            _azure_stream_chunks(["net ", "ok"])
        )
        result = list(ai.analyze_report_stream("report"))
        assert result == ["net ", "ok"]

    def test_amazon_yields_chunks(self):
        ai = _make_ai("amazon")
        ai._amazon_client = MagicMock()
        ai._amazon_client.invoke_model_with_response_stream.return_value = {
            "body": _bedrock_events(["Hello", " world"])
        }
        result = list(ai.analyze_report_stream("report"))
        assert result == ["Hello", " world"]

    def test_unknown_provider_yields_nothing(self):
        ai = _make_ai("unknown")
        result = list(ai.analyze_report_stream("report"))
        assert result == []

    def test_sanitizes_report_before_prompting(self):
        """Control characters in the report must not reach the LLM prompt."""
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        ai._google_model.generate_content.return_value = _gemini_stream_chunks(["ok"])

        malicious_report = "Packet Loss: 5%\x00\x01\x1b[31mmalicious"
        list(ai.analyze_report_stream(malicious_report))

        call_args = ai._google_model.generate_content.call_args[0][0]
        assert "\x00" not in call_args
        assert "\x01" not in call_args


# ── Feature 2: chat ───────────────────────────────────────────────────────────

class TestChatGoogle:
    def test_converts_assistant_to_model_role(self):
        ai = _make_ai("google")
        mock_session = MagicMock()
        mock_session.send_message.return_value = MagicMock(text="reply")
        ai._google_model = MagicMock()
        ai._google_model.start_chat.return_value = mock_session

        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
        ]
        ai._chat_google(messages)

        history_passed = ai._google_model.start_chat.call_args[1]["history"]
        roles = [h["role"] for h in history_passed]
        assert "model" in roles   # assistant → model
        assert "user" in roles

    def test_system_message_fused_to_first_user(self):
        ai = _make_ai("google")
        mock_session = MagicMock()
        mock_session.send_message.return_value = MagicMock(text="ok")
        ai._google_model = MagicMock()
        ai._google_model.start_chat.return_value = mock_session

        messages = [
            {"role": "system", "content": "Be a network expert."},
            {"role": "user", "content": "What is latency?"},
        ]
        ai._chat_google(messages)
        sent = mock_session.send_message.call_args[0][0]
        assert "Be a network expert." in sent

    def test_empty_messages_returns_fallback(self):
        ai = _make_ai("google")
        result = ai._chat_google([])
        assert "No messages" in result


class TestChatRouting:
    def test_routes_to_google(self):
        ai = _make_ai("google")
        mock_session = MagicMock()
        mock_session.send_message.return_value = MagicMock(text="goog")
        ai._google_model = MagicMock()
        ai._google_model.start_chat.return_value = mock_session
        assert ai.chat([{"role": "user", "content": "ping"}]) == "goog"

    def test_unknown_provider_returns_error(self):
        ai = _make_ai("unknown")
        result = ai.chat([{"role": "user", "content": "ping"}])
        assert "not configured" in result.lower()


# ── Feature 5: generate_briefing ──────────────────────────────────────────────

class TestGenerateBriefing:
    def test_returns_string(self):
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        ai._google_model.generate_content.return_value = MagicMock(
            text="# Network Briefing\n\n## Overview\nLatency: 12 ms"
        )
        result = ai.generate_briefing({"latency_ms": "12", "status": "Success"})
        assert isinstance(result, str)
        assert "Network Briefing" in result

    def test_unknown_provider_returns_fallback(self):
        ai = _make_ai("unknown")
        result = ai.generate_briefing({"latency_ms": "12"})
        assert "not configured" in result.lower()

    def test_prompt_includes_simulation_data(self):
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        ai._google_model.generate_content.return_value = MagicMock(text="# Briefing")

        ai.generate_briefing({"source": "51.5, -0.12", "destination": "Berlin"})
        call_prompt = ai._google_model.generate_content.call_args[0][0]
        assert "51.5" in call_prompt
        assert "Berlin" in call_prompt
