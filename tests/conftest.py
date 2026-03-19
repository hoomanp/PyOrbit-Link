"""
Shared pytest configuration for PyOrbit-Link + ConstellaSim test suite.

Sets FLASK_SECRET_KEY and sys.path BEFORE any app module is imported.
The root /LOS directory contains stale copies of pyorbit_link/ and mobile_client/
without the new features; we must ensure PyOrbit-Link/ and ConstellaSim/ paths
come FIRST in sys.path so the feature-complete versions are imported.
"""
import os
import sys

# ── Must be set before any Flask app is imported ─────────────────────────────
os.environ["FLASK_SECRET_KEY"] = "ci-cd-test-secret-key-do-not-use-in-prod"
os.environ.setdefault("SAT_AI_PROVIDER", "google")
os.environ.setdefault("NETWORK_AI_PROVIDER", "google")
# Strip real AI keys so MissionAI/NetworkAI init always fails gracefully
for _k in ("GOOGLE_API_KEY", "AZURE_OPENAI_KEY", "AZURE_OPENAI_ENDPOINT", "AWS_REGION"):
    os.environ.pop(_k, None)

# ── Source paths — inserted at front to shadow stale root-level copies ────────
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PYORBIT_SRC = os.path.join(_ROOT, "PyOrbit-Link")
_CONSTEL_SRC = os.path.join(_ROOT, "ConstellaSim")

# Insert at position 0 so these shadow anything already on the path
sys.path.insert(0, _CONSTEL_SRC)
sys.path.insert(0, _PYORBIT_SRC)

# Remove the root LOS dir from sys.path to prevent stale packages from shadowing
# (pytest adds CWD = _ROOT automatically; we remove it to avoid conflicts)
for _p in list(sys.path):
    if os.path.abspath(_p) == _ROOT and _p in sys.path:
        sys.path.remove(_p)
        break

# Clear any stale cached modules so our path inserts take effect
for _mod in list(sys.modules.keys()):
    if _mod.startswith(("pyorbit_link", "constellasim", "mobile_client")):
        del sys.modules[_mod]

# ── Shared test data ──────────────────────────────────────────────────────────
# Real-format ISS TLE (epoch doesn't need to be current for unit tests)
MOCK_TLE = (
    "ISS (ZARYA)",
    "1 25544U 98067A   24001.50000000  .00016717  00000+0  10270-3 0  9994",
    "2 25544  51.6400 208.9163 0006827  86.2477 273.9397 15.52444741421788",
)
