"""Feature 3: Natural Language Mission Planner (NL2Function) for PyOrbit-Link."""

import json
import re
import logging

logger = logging.getLogger(__name__)

# Strict allowlist — only these function names may be executed.
_ALLOWED_FUNCTIONS = {"track", "find_events", "calculate_fspl"}

_FUNCTION_SCHEMAS = {
    "track": {
        "description": "Track ISS position from a ground location. Returns azimuth, elevation, distance, and FSPL.",
        "params": {
            "city": "string (optional) — city name to look up, e.g. 'Tokyo'",
            "lat": "float (optional) — latitude if city is not provided",
            "lon": "float (optional) — longitude if city is not provided",
        },
    },
    "find_events": {
        "description": "Find the next ISS pass windows over a ground location.",
        "params": {
            "city": "string (optional) — city name",
            "lat": "float (optional) — latitude if city not provided",
            "lon": "float (optional) — longitude if city not provided",
        },
    },
    "calculate_fspl": {
        "description": "Calculate Free Space Path Loss for a given frequency and distance.",
        "params": {
            "freq_hz": "float — signal frequency in Hz, e.g. 2.4e9 for 2.4 GHz",
            "dist_km": "float — slant range in kilometres",
        },
    },
}

_SYSTEM_PROMPT = (
    "You are a satellite mission planning assistant. "
    "Parse the user's natural language request and return ONLY a JSON object "
    "with two keys: \"function\" (one of the available function names) and \"params\" "
    "(an object with the required parameters). "
    "Do not include any explanation or markdown — only raw JSON.\n\n"
    "Available functions:\n"
    + json.dumps(_FUNCTION_SCHEMAS, indent=2)
    + "\n\nIf you cannot map the request to any function, return: "
    "{\"function\": null, \"params\": {}}"
)


class MissionPlanner:
    """Parse plain-English mission commands into executable function calls."""

    def __init__(self, ai_client):
        self._ai = ai_client

    def parse(self, user_text):
        """
        Returns dict: {"function": str|None, "params": dict}
        Validates the function name against the allowlist before returning.
        """
        if not user_text or not user_text.strip():
            return {"function": None, "params": {}}

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_text.strip()[:500]},
        ]

        try:
            raw = self._ai.chat(messages)
            parsed = self._extract_json(raw)
        except Exception:
            logger.exception("MissionPlanner LLM call failed")
            return {"function": None, "params": {}}

        func_name = parsed.get("function")
        params = parsed.get("params", {})

        if func_name not in _ALLOWED_FUNCTIONS:
            return {"function": None, "params": {}}

        if not isinstance(params, dict):
            return {"function": None, "params": {}}

        return {"function": func_name, "params": params}

    @staticmethod
    def _extract_json(text):
        """Extract JSON from LLM response even if surrounded by markdown fences."""
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?", "", text).strip()
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Fall back to finding the first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"function": None, "params": {}}
