import os
import re
import json
import glob
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Optimization: cap total KB content to prevent runaway token costs and memory use.
_MAX_KB_CHARS = 50_000

# Security: pattern to strip ASCII control characters and Unicode bidirectional
# overrides that can be used for prompt injection.
_CONTROL_CHARS_RE = re.compile(
    r'[\x00-\x1f\x7f\u200b-\u200d\u202a-\u202e\u2066-\u2069]'
)

def _sanitize(text):
    """Strip control characters and bidirectional overrides from any string."""
    return _CONTROL_CHARS_RE.sub(' ', str(text)).strip()


class MissionAI:
    """RAG-Enabled AI Assistant for Satellite Systems Engineering."""

    def __init__(self, provider=None):
        self.provider = provider or os.getenv("SAT_AI_PROVIDER", "google").lower()
        self.kb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'knowledge_base'))
        # Security: assert kb_path stays within the project tree to prevent path traversal.
        # Use if/raise instead of assert — assert is compiled away with python -O.
        _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if not self.kb_path.startswith(_project_root):
            raise ValueError(f"kb_path '{self.kb_path}' resolves outside project directory")
        # Optimization: load KB once at startup; re-reading every request wastes I/O and tokens.
        self._kb_cache = self._load_kb()
        # Optimization: build AI clients once to reuse HTTP sessions across requests.
        self._azure_client = None
        self._amazon_client = None
        self._google_model = None
        self._init_clients()

    def _load_kb(self):
        """Load and cache all knowledge base documents, capped at _MAX_KB_CHARS."""
        kb_content = ""
        for file_path in glob.glob(os.path.join(self.kb_path, "*.txt")):
            # Security: resolve symlinks and verify each file stays within kb_path.
            resolved = os.path.realpath(file_path)
            if not resolved.startswith(os.path.realpath(self.kb_path)):
                continue
            with open(resolved, 'r') as f:
                kb_content += f"\n--- Document: {os.path.basename(file_path)} ---\n"
                kb_content += f.read() + "\n"
            if len(kb_content) >= _MAX_KB_CHARS:
                break
        return kb_content[:_MAX_KB_CHARS]

    def _get_kb_context(self):
        return self._kb_cache

    def _init_clients(self):
        """Initialize AI clients once at startup for connection reuse."""
        # V-05: validate required secrets at boot so misconfigured deployments fail fast.
        if self.provider == "azure":
            key = os.getenv("AZURE_OPENAI_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            if not key or not endpoint:
                raise RuntimeError("AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT must be set for azure provider")
            from openai import AzureOpenAI
            self._azure_client = AzureOpenAI(
                api_key=key,
                api_version="2024-02-15-preview",
                azure_endpoint=endpoint
            )
        elif self.provider == "amazon":
            import boto3
            self._amazon_client = boto3.client("bedrock-runtime", region_name="us-east-1")
        elif self.provider == "google":
            key = os.getenv("GOOGLE_API_KEY")
            if not key:
                raise RuntimeError("GOOGLE_API_KEY must be set for google provider")
            import google.generativeai as genai
            genai.configure(api_key=key)
            self._google_model = genai.GenerativeModel('gemini-1.5-flash')

    def _sanitize_telemetry(self, data):
        """Sanitize string values in telemetry dicts to prevent prompt injection."""
        if isinstance(data, dict):
            return {k: self._sanitize_telemetry(v) for k, v in data.items()}
        if isinstance(data, str):
            return _sanitize(data)
        return data

    def get_analysis(self, user_prompt, telemetry_data):
        """Asks the AI to analyze data while GROUNDED in technical documentation."""
        kb_context = self._get_kb_context()
        # Security: strip all control characters (not just \n/\r) to prevent prompt injection.
        safe_prompt = _sanitize(user_prompt)
        safe_telemetry = self._sanitize_telemetry(telemetry_data)

        system_instructions = (
            "You are a Satellite Systems Engineer specializing in LEO constellations (e.g., Kuiper, Starlink).\n"
            "Use the provided Technical Standards context to justify your analysis.\n"
            "If the telemetry data violates any standard (e.g., elevation too low), highlight it as a 'Mission Risk'."
        )

        full_prompt = (
            f"{system_instructions}\n\n"
            f"--- TECHNICAL STANDARDS CONTEXT ---\n{kb_context}\n"
            f"--- CURRENT TELEMETRY ---\n{json.dumps(safe_telemetry, indent=2)}\n\n"
            f"USER REQUEST: {safe_prompt}\n"
            "Provide a highly detailed, grounded response."
        )

        if self.provider == "azure":
            return self._call_azure(full_prompt)
        elif self.provider == "amazon":
            return self._call_amazon(full_prompt)
        elif self.provider == "google":
            return self._call_google(full_prompt)
        else:
            return "AI Provider not configured correctly."

    def _call_azure(self, prompt):
        response = self._azure_client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4-turbo"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def _call_amazon(self, prompt):
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}]
        })
        response = self._amazon_client.invoke_model(body=body, modelId="anthropic.claude-3-sonnet-20240229-v1:0")
        return json.loads(response.get("body").read())["content"][0]["text"]

    def _call_google(self, prompt):
        response = self._google_model.generate_content(prompt)
        return response.text
