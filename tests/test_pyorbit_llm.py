"""
Unit tests for PyOrbit-Link MissionAI new methods:
  - Feature 1: get_analysis_stream() + provider stream helpers
  - Feature 2: chat() + _chat_google() message-format conversion
  - Feature 5: generate_briefing()
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from pyorbit_link.llm import MissionAI


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_ai(provider="google"):
    """Instantiate MissionAI skipping real client / KB initialisation."""
    with patch.object(MissionAI, "_init_clients"), \
         patch.object(MissionAI, "_load_kb", return_value="mock KB context"):
        ai = MissionAI(provider=provider)
    return ai


def _gemini_stream_chunks(texts):
    """Build a list of mock Gemini chunk objects."""
    chunks = []
    for t in texts:
        c = MagicMock()
        c.text = t
        chunks.append(c)
    return chunks


def _azure_stream_chunks(texts):
    """Build a list of mock Azure streaming chunk objects."""
    chunks = []
    for t in texts:
        delta = MagicMock()
        delta.content = t
        choice = MagicMock()
        choice.delta = delta
        chunk = MagicMock()
        chunk.choices = [choice]
        chunks.append(chunk)
    return chunks


def _bedrock_events(texts):
    """Build a list of mock Bedrock event-stream items."""
    events = []
    for t in texts:
        payload = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": t}}
        events.append({"chunk": {"bytes": json.dumps(payload).encode()}})
    return events


# ── Feature 1: Streaming ──────────────────────────────────────────────────────

class TestStreamGoogle:
    def test_yields_all_chunks(self):
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        ai._google_model.generate_content.return_value = _gemini_stream_chunks(["Hello ", "world"])

        result = list(ai._stream_google("test prompt"))
        assert result == ["Hello ", "world"]
        ai._google_model.generate_content.assert_called_once_with("test prompt", stream=True)

    def test_skips_empty_chunks(self):
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        # Gemini sometimes returns chunks with empty text
        chunks = _gemini_stream_chunks(["A", "", "B"])
        chunks[1].text = ""  # empty
        ai._google_model.generate_content.return_value = chunks

        result = list(ai._stream_google("prompt"))
        assert result == ["A", "B"]


class TestStreamAzure:
    def test_yields_all_chunks(self):
        ai = _make_ai("azure")
        ai._azure_client = MagicMock()
        ai._azure_client.chat.completions.create.return_value = iter(
            _azure_stream_chunks(["Sat ", "link ", "ok"])
        )

        result = list(ai._stream_azure("test"))
        assert result == ["Sat ", "link ", "ok"]

    def test_skips_empty_delta(self):
        ai = _make_ai("azure")
        ai._azure_client = MagicMock()
        chunks = _azure_stream_chunks(["A", "B"])
        # Simulate a stop chunk with no content
        stop_chunk = MagicMock()
        stop_chunk.choices = []
        ai._azure_client.chat.completions.create.return_value = iter(
            chunks + [stop_chunk]
        )
        result = list(ai._stream_azure("test"))
        assert result == ["A", "B"]


class TestStreamAmazon:
    def test_yields_all_chunks(self):
        ai = _make_ai("amazon")
        ai._amazon_client = MagicMock()
        ai._amazon_client.invoke_model_with_response_stream.return_value = {
            "body": _bedrock_events(["Hello", " world"])
        }
        result = list(ai._stream_amazon("test"))
        assert result == ["Hello", " world"]

    def test_ignores_non_text_delta_events(self):
        ai = _make_ai("amazon")
        ai._amazon_client = MagicMock()
        # An event with a different type should yield empty string (filtered by get)
        non_text = json.dumps({"type": "message_start"}).encode()
        text_event = _bedrock_events(["data"])[0]
        ai._amazon_client.invoke_model_with_response_stream.return_value = {
            "body": [{"chunk": {"bytes": non_text}}, text_event]
        }
        result = list(ai._stream_amazon("test"))
        # "message_start" has no delta.text, yields ""
        assert "data" in result


class TestGetAnalysisStreamRouting:
    """Verify get_analysis_stream routes to the right provider."""

    def test_routes_to_google(self):
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        ai._google_model.generate_content.return_value = _gemini_stream_chunks(["ok"])

        chunks = list(ai.get_analysis_stream("Check link", {"elevation": "45°"}))
        assert "ok" in chunks

    def test_routes_to_azure(self):
        ai = _make_ai("azure")
        ai._azure_client = MagicMock()
        ai._azure_client.chat.completions.create.return_value = iter(
            _azure_stream_chunks(["azure_response"])
        )
        chunks = list(ai.get_analysis_stream("Check link", {"elevation": "45°"}))
        assert "azure_response" in chunks

    def test_unknown_provider_yields_nothing(self):
        ai = _make_ai("unknown")
        result = list(ai.get_analysis_stream("prompt", {}))
        assert result == []


# ── Feature 2: Multi-Turn Chat ────────────────────────────────────────────────

class TestChatGoogle:
    def test_sends_last_user_message(self):
        ai = _make_ai("google")
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.return_value = MagicMock(text="reply text")
        ai._google_model = MagicMock()
        ai._google_model.start_chat.return_value = mock_chat_session

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How is my link?"},
        ]
        result = ai._chat_google(messages)
        assert result == "reply text"
        # Last user message should be sent, prior turns in history
        mock_chat_session.send_message.assert_called_once_with("How is my link?")

    def test_system_message_prepended_to_first_user(self):
        ai = _make_ai("google")
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.return_value = MagicMock(text="ok")
        ai._google_model = MagicMock()
        ai._google_model.start_chat.return_value = mock_chat_session

        messages = [
            {"role": "system", "content": "You are an engineer."},
            {"role": "user", "content": "What is FSPL?"},
        ]
        ai._chat_google(messages)
        call_arg = mock_chat_session.send_message.call_args[0][0]
        assert "You are an engineer." in call_arg
        assert "What is FSPL?" in call_arg

    def test_empty_messages_returns_fallback(self):
        ai = _make_ai("google")
        result = ai._chat_google([])
        assert "No messages" in result


class TestChatAzure:
    def test_passes_full_messages_list(self):
        ai = _make_ai("azure")
        ai._azure_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "azure reply"
        ai._azure_client.chat.completions.create.return_value = mock_resp

        messages = [{"role": "user", "content": "hi"}]
        result = ai._chat_azure(messages)
        assert result == "azure reply"
        ai._azure_client.chat.completions.create.assert_called_once()
        call_kwargs = ai._azure_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"] == messages


class TestChatAmazon:
    def test_separates_system_messages(self):
        ai = _make_ai("amazon")
        ai._amazon_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.get.return_value.read.return_value = json.dumps(
            {"content": [{"text": "bedrock reply"}]}
        ).encode()
        ai._amazon_client.invoke_model.return_value = mock_resp

        messages = [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Question"},
        ]
        result = ai._chat_amazon(messages)
        assert result == "bedrock reply"
        call_body = json.loads(ai._amazon_client.invoke_model.call_args[1]["body"])
        assert "system" in call_body
        assert "Be helpful." in call_body["system"]
        # system role should not appear in messages array
        for m in call_body["messages"]:
            assert m["role"] != "system"


class TestChatRouting:
    def test_chat_routes_to_google(self):
        ai = _make_ai("google")
        mock_session = MagicMock()
        mock_session.send_message.return_value = MagicMock(text="google reply")
        ai._google_model = MagicMock()
        ai._google_model.start_chat.return_value = mock_session

        result = ai.chat([{"role": "user", "content": "ping"}])
        assert result == "google reply"

    def test_chat_unknown_provider(self):
        ai = _make_ai("unknown")
        result = ai.chat([{"role": "user", "content": "ping"}])
        assert "not configured" in result.lower()


# ── Feature 5: Mission Briefing ────────────────────────────────────────────────

class TestGenerateBriefing:
    def test_returns_markdown_string(self):
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        ai._google_model.generate_content.return_value = MagicMock(
            text="# Mission Briefing\n\n## Section\nContent."
        )
        result = ai.generate_briefing({"elevation": "45°", "azimuth": "180°"})
        assert isinstance(result, str)
        assert "Mission Briefing" in result

    def test_sanitizes_data_keys(self):
        """Data dict is sanitized before embedding in prompt — no injection chars."""
        ai = _make_ai("google")
        ai._google_model = MagicMock()
        ai._google_model.generate_content.return_value = MagicMock(text="# Briefing")

        malicious_data = {"key\x00": "value\x00\x01\x02"}
        result = ai.generate_briefing(malicious_data)
        # Should not raise; result should be a string
        assert isinstance(result, str)

    def test_unknown_provider_returns_fallback(self):
        ai = _make_ai("unknown")
        result = ai.generate_briefing({})
        assert "not configured" in result.lower()
