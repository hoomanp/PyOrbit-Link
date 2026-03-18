from flask import Flask, render_template_string, jsonify, request, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
import os
import secrets
import logging
import threading
from datetime import datetime, timezone

# Add the parent directory to sys.path to import pyorbit_link
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyorbit_link.tracker import SatTracker
from pyorbit_link.api import CelesTrakAPI
from pyorbit_link.calculator import LinkCalculator
from pyorbit_link.llm import MissionAI

app = Flask(__name__)
# M-6: require an explicit secret key so sessions are cryptographically sound.
_secret = os.getenv("FLASK_SECRET_KEY")
if not _secret:
    raise RuntimeError("FLASK_SECRET_KEY environment variable must be set")
app.secret_key = _secret
# C-2: cap incoming JSON body size to 1 KB — lat/lon payload needs no more.
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024
# M-1: trust the first X-Forwarded-For hop from the reverse proxy (Replit/Railway/Render)
# so flask-limiter sees the real client IP rather than the proxy IP.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "30 per minute"])
# H-3: wrap MissionAI init so a missing API key degrades gracefully instead of
# crashing the entire app at startup.
try:
    ai_assistant = MissionAI()
except Exception:
    logging.getLogger(__name__).exception("Failed to initialize MissionAI — AI analysis will be unavailable")
    ai_assistant = None

@app.before_request
def generate_csp_nonce():
    """Generate a per-request nonce for use in CSP and script tags."""
    g.csp_nonce = secrets.token_urlsafe(16)

@app.after_request
def set_security_headers(response):
    """Add browser-level security headers to every response."""
    nonce = getattr(g, 'csp_nonce', '')
    # H-4: apply nonce to style-src as well, removing 'unsafe-inline' entirely.
    response.headers['Content-Security-Policy'] = (
        f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; style-src 'self' 'nonce-{nonce}'"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    # M-4: instruct browsers to enforce HTTPS for 2 years.
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains'
    return response

# TLE data has a short validity window (~6 hours for ISS).
# Cache the tracker and refresh it periodically to keep orbit predictions accurate.
_TLE_TTL_SECONDS = 6 * 3600
_tle_lock = threading.Lock()
_tle_fetched_at = None
TLE_CACHE = None
_tracker = None

def _refresh_tle_if_stale():
    """Re-fetch TLE data when it is older than _TLE_TTL_SECONDS."""
    global TLE_CACHE, _tracker, _tle_fetched_at
    with _tle_lock:
        now = datetime.now(timezone.utc)
        if _tle_fetched_at and (now - _tle_fetched_at).total_seconds() < _TLE_TTL_SECONDS:
            return  # still fresh
        fresh = CelesTrakAPI.get_tle_by_norad_id(25544)
        if fresh:
            TLE_CACHE = fresh
            _name, _l1, _l2 = fresh
            _tracker = SatTracker(_l1, _l2, _name)
            _tle_fetched_at = now

# Initial fetch at startup.
_refresh_tle_if_stale()

@app.route('/')
def home():
    """Renders the Mobile UI."""
    return render_template_string(HTML_TEMPLATE, nonce=g.csp_nonce)

@app.route('/api/track', methods=['POST'])
@limiter.limit("30 per minute")
def track_iss():
    """API Endpoint: Receives GPS coordinates, returns next pass."""
    # Security fix: validate all inputs before use.
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        lat = float(data['latitude'])
        lon = float(data['longitude'])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "latitude and longitude must be valid numbers"}), 400
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return jsonify({"error": "Coordinates out of range"}), 400

    _refresh_tle_if_stale()
    if not _tracker:
        return jsonify({"error": "Could not fetch TLE data."}), 500

    name = TLE_CACHE[0]
    tracker = _tracker

    # Calculate current position (Az/El/Range)
    az, el, dist_km = tracker.get_aer(lat, lon, alt_m=10.0)
    
    # Calculate Link Budget (2.4 GHz WiFi example)
    freq = 2.4e9
    fspl = LinkCalculator.calculate_fspl(freq, dist_km)
    
    telemetry = {
        "azimuth": f"{az:.2f}°",
        "elevation": f"{el:.2f}°",
        "distance": f"{dist_km:.2f} km",
        "fspl_db": f"{fspl:.2f} dB"
    }

    # Use AI to analyze the link
    try:
        if ai_assistant is None:
            raise RuntimeError("AI not configured")
        ai_analysis = ai_assistant.get_analysis(
            "Analyze this satellite link budget. Is the signal too weak for a 2.4GHz WiFi link? Suggest improvements.",
            telemetry
        )
    except Exception:
        # Security: log full exception server-side; return generic message to avoid leaking
        # API endpoint URLs, credentials, or internal state to the client.
        app.logger.exception("AI analysis failed")
        ai_analysis = "AI analysis temporarily unavailable."

    # Find next pass
    passes = tracker.find_events(lat, lon, alt_m=10.0, duration_days=1)
    next_pass = passes[0] if passes else None
    
    return jsonify({
        "sat_name": name,
        "azimuth": telemetry["azimuth"],
        "elevation": telemetry["elevation"],
        "distance": telemetry["distance"],
        "fspl_db": telemetry["fspl_db"],
        "ai_analysis": ai_analysis,
        "next_pass": next_pass
    })

# --- Mobile HTML/JS Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>PyOrbit-Link Mobile AI</title>
    <style nonce="{{ nonce }}">
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f1f5f9; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; margin: 15px auto; max-width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h1 { font-size: 1.5rem; margin-bottom: 10px; color: #38bdf8; }
        button { background: #0ea5e9; color: white; border: none; padding: 15px 30px; font-size: 1.1rem; border-radius: 50px; cursor: pointer; width: 100%; max-width: 300px; transition: background 0.2s; }
        button:active { background: #0284c7; transform: scale(0.98); }
        .data-row { display: flex; justify-content: space-between; margin: 10px 0; border-bottom: 1px solid #334155; padding-bottom: 5px; }
        .label { color: #94a3b8; }
        .value { font-weight: bold; }
        #status { margin-top: 15px; color: #fbbf24; font-size: 0.9rem; }
        .ai-box { background: #0c4a6e; border-left: 4px solid #38bdf8; padding: 15px; text-align: left; font-size: 0.9rem; margin-top: 20px; border-radius: 4px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <h1>🛰️ PyOrbit-Link AI</h1>
    <p>Live Tracking & Smart Link Analysis</p>
    
    <div class="card">
        <button onclick="getLocation()">📍 Use My Location</button>
        <div id="status">Ready to track...</div>
    </div>

    <div id="results" class="card hidden">
        <h3>Live Telemetry</h3>
        <div class="data-row"><span class="label">Satellite</span><span class="value" id="sat_name">-</span></div>
        <div class="data-row"><span class="label">Azimuth</span><span class="value" id="azimuth">-</span></div>
        <div class="data-row"><span class="label">Elevation</span><span class="value" id="elevation">-</span></div>
        <div class="data-row"><span class="label">Distance</span><span class="value" id="distance">-</span></div>
        <div class="data-row"><span class="label">Link Loss (FSPL)</span><span class="value" id="fspl">-</span></div>
        
        <h3>🤖 AI Mission Analysis</h3>
        <div id="ai_analysis" class="ai-box">Analyzing link...</div>

        <h3>Next Pass</h3>
        <div class="data-row"><span class="label">Rise Time</span><span class="value" id="pass_rise">-</span></div>
        <div class="data-row"><span class="label">Set Time</span><span class="value" id="pass_set">-</span></div>
    </div>

    <script nonce="{{ nonce }}">
        function getLocation() {
            const status = document.getElementById('status');
            if (!navigator.geolocation) {
                status.textContent = "Geolocation is not supported by your browser";
                return;
            }
            status.textContent = "Acquiring GPS Signal...";
            navigator.geolocation.getCurrentPosition(success, error);
        }

        function success(position) {
            const status = document.getElementById('status');
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            status.textContent = `GPS Locked: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
            
            fetch('/api/track', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({latitude: lat, longitude: lon})
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('results').classList.remove('hidden');
                document.getElementById('sat_name').textContent = data.sat_name;
                document.getElementById('azimuth').textContent = data.azimuth;
                document.getElementById('elevation').textContent = data.elevation;
                document.getElementById('distance').textContent = data.distance;
                document.getElementById('fspl').textContent = data.fspl_db;
                document.getElementById('ai_analysis').textContent = data.ai_analysis;
                
                if(data.next_pass) {
                    document.getElementById('pass_rise').textContent = new Date(data.next_pass.Rise).toLocaleTimeString();
                    document.getElementById('pass_set').textContent = new Date(data.next_pass.Set).toLocaleTimeString();
                } else {
                    document.getElementById('pass_rise').textContent = "None soon";
                }
                status.textContent = "Tracking Complete ✅";
            })
            .catch(err => {
                status.textContent = "Server Error ❌";
                console.error(err);
            });
        }

        function error() {
            document.getElementById('status').textContent = "Unable to retrieve your location ❌";
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # Security fix: debug=True exposes an interactive debugger; use env var to control it.
    # FLASK_HOST defaults to 0.0.0.0 for mobile access; set to 127.0.0.1 for local-only use.
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    # PORT env var is set automatically by Replit, Railway, Render, and similar platforms.
    port = int(os.getenv("PORT", 5000))
    app.run(host=host, port=port, debug=debug)
