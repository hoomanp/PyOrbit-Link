from flask import Flask, render_template_string, jsonify, request, g, session, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
import os
import secrets
import logging
import threading
import json
from datetime import datetime, timezone

# Add the parent directory to sys.path to import pyorbit_link
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyorbit_link.tracker import SatTracker
from pyorbit_link.api import CelesTrakAPI
from pyorbit_link.calculator import LinkCalculator
from pyorbit_link.llm import MissionAI
from pyorbit_link.utils import LocationProvider
from pyorbit_link.planner import MissionPlanner
from pyorbit_link.monitor import AnomalyMonitor

app = Flask(__name__)
# M-6: require an explicit secret key so sessions are cryptographically sound.
_secret = os.getenv("FLASK_SECRET_KEY")
if not _secret:
    raise RuntimeError("FLASK_SECRET_KEY environment variable must be set")
app.secret_key = _secret
# Raise to 8 KB to accommodate chat message history in POST bodies.
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024
# M-1: trust the first X-Forwarded-For hop from the reverse proxy.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "30 per minute"])

# H-3: wrap MissionAI init so a missing API key degrades gracefully.
try:
    ai_assistant = MissionAI()
except Exception:
    logging.getLogger(__name__).exception("Failed to initialize MissionAI — AI analysis will be unavailable")
    ai_assistant = None

# Feature 3: NL planner (shares the existing AI client).
_planner = MissionPlanner(ai_assistant) if ai_assistant else None

# Shared geocoder instance (caches results across requests).
_location_provider = LocationProvider()

# Feature 4: Anomaly monitor (opt-in via ANOMALY_MONITOR=true).
_monitor = None
if os.getenv("ANOMALY_MONITOR", "").lower() == "true" and ai_assistant:
    _monitor = AnomalyMonitor(ai_assistant)

# Feature 5: Last telemetry snapshot for the briefing endpoint.
_last_telemetry: dict = {}
_telemetry_lock = threading.Lock()

if _monitor:
    _monitor.set_telemetry_source(_last_telemetry, _telemetry_lock)
    _monitor.start()

# --- TLE cache ---
_TLE_TTL_SECONDS = 6 * 3600
_tle_lock = threading.Lock()
_tle_fetched_at = None
TLE_CACHE = None
_tracker = None


def _refresh_tle_if_stale():
    global TLE_CACHE, _tracker, _tle_fetched_at
    with _tle_lock:
        now = datetime.now(timezone.utc)
        if _tle_fetched_at and (now - _tle_fetched_at).total_seconds() < _TLE_TTL_SECONDS:
            return
        fresh = CelesTrakAPI.get_tle_by_norad_id(25544)
        if fresh:
            TLE_CACHE = fresh
            _name, _l1, _l2 = fresh
            _tracker = SatTracker(_l1, _l2, _name)
            _tle_fetched_at = now


_refresh_tle_if_stale()


@app.before_request
def generate_csp_nonce():
    g.csp_nonce = secrets.token_urlsafe(16)


@app.after_request
def set_security_headers(response):
    nonce = getattr(g, 'csp_nonce', '')
    response.headers['Content-Security-Policy'] = (
        f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; style-src 'self' 'nonce-{nonce}'"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains'
    return response


@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, nonce=g.csp_nonce)


def _compute_telemetry(lat, lon):
    """Shared helper: compute AER + FSPL + next pass for a given observer position."""
    _refresh_tle_if_stale()
    if not _tracker:
        return None, "Could not fetch TLE data."
    name = TLE_CACHE[0]
    az, el, dist_km = _tracker.get_aer(lat, lon, alt_m=10.0)
    freq = 2.4e9
    fspl = LinkCalculator.calculate_fspl(freq, dist_km)
    telemetry = {
        "azimuth": f"{az:.2f}°",
        "elevation": f"{el:.2f}°",
        "distance": f"{dist_km:.2f} km",
        "fspl_db": f"{fspl:.2f} dB",
    }
    passes = _tracker.find_events(lat, lon, alt_m=10.0, duration_days=1)
    next_pass = passes[0] if passes else None
    return {"name": name, "telemetry": telemetry, "next_pass": next_pass}, None


# --- Original blocking track endpoint (kept for API compatibility) ---
@app.route('/api/track', methods=['POST'])
@limiter.limit("30 per minute")
def track_iss():
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

    result, err = _compute_telemetry(lat, lon)
    if err:
        return jsonify({"error": err}), 500

    telemetry = result["telemetry"]
    with _telemetry_lock:
        _last_telemetry.update(telemetry)
        _last_telemetry["sat_name"] = result["name"]
        _last_telemetry["observer_lat"] = lat
        _last_telemetry["observer_lon"] = lon
        _last_telemetry["timestamp"] = datetime.now(timezone.utc).isoformat()

    try:
        if ai_assistant is None:
            raise RuntimeError("AI not configured")
        ai_analysis = ai_assistant.get_analysis(
            "Analyze this satellite link budget. Is the signal too weak for a 2.4GHz WiFi link? Suggest improvements.",
            telemetry,
        )
    except Exception:
        app.logger.exception("AI analysis failed")
        ai_analysis = "AI analysis temporarily unavailable."

    return jsonify({
        "sat_name": result["name"],
        "azimuth": telemetry["azimuth"],
        "elevation": telemetry["elevation"],
        "distance": telemetry["distance"],
        "fspl_db": telemetry["fspl_db"],
        "ai_analysis": ai_analysis,
        "next_pass": result["next_pass"],
    })


# --- Feature 1: Streaming SSE endpoint ---
@app.route('/api/track/stream')
@limiter.limit("30 per minute")
def track_iss_stream():
    try:
        lat = float(request.args.get('lat', ''))
        lon = float(request.args.get('lon', ''))
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lon query params are required"}), 400
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return jsonify({"error": "Coordinates out of range"}), 400

    result, err = _compute_telemetry(lat, lon)
    if err:
        return jsonify({"error": err}), 500

    telemetry = result["telemetry"]
    with _telemetry_lock:
        _last_telemetry.update(telemetry)
        _last_telemetry["sat_name"] = result["name"]
        _last_telemetry["observer_lat"] = lat
        _last_telemetry["observer_lon"] = lon
        _last_telemetry["timestamp"] = datetime.now(timezone.utc).isoformat()

    telemetry_payload = {
        "sat_name": result["name"],
        **telemetry,
        "next_pass": result["next_pass"],
    }

    def generate():
        yield f"event: telemetry\ndata: {json.dumps(telemetry_payload)}\n\n"
        if ai_assistant is None:
            yield f"data: {json.dumps('AI analysis unavailable.')}\n\n"
        else:
            try:
                for chunk in ai_assistant.get_analysis_stream(
                    "Analyze this satellite link budget. Is the signal too weak for a 2.4GHz WiFi link? Suggest improvements.",
                    telemetry,
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception:
                app.logger.exception("Streaming AI analysis failed")
                yield f"data: {json.dumps('AI analysis error.')}\n\n"
        yield "event: done\ndata: {}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


# --- Feature 2: Multi-turn chat ---
_MAX_CHAT_TURNS = 10


@app.route('/api/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    if ai_assistant is None:
        return jsonify({"error": "AI not configured"}), 503
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    user_msg = data.get("message", "")
    if not isinstance(user_msg, str) or not user_msg.strip():
        return jsonify({"error": "message must be a non-empty string"}), 400
    user_msg = user_msg.strip()[:1000]

    from pyorbit_link.llm import _sanitize
    user_msg = _sanitize(user_msg)

    history = session.get("chat_history", [])

    # Inject system context on first turn.
    if not history:
        with _telemetry_lock:
            snapshot = dict(_last_telemetry)
        system_content = (
            "You are a Satellite Systems Engineer. Answer follow-up questions about the current "
            "tracking session. Current telemetry snapshot:\n"
            + json.dumps(snapshot, indent=2)
        )
        history = [{"role": "system", "content": system_content}]

    history.append({"role": "user", "content": user_msg})

    try:
        reply = ai_assistant.chat(history)
    except Exception:
        app.logger.exception("Chat AI call failed")
        return jsonify({"error": "AI temporarily unavailable."}), 503

    history.append({"role": "assistant", "content": reply})

    # Cap history: keep system message + last N turn pairs.
    max_msgs = 1 + _MAX_CHAT_TURNS * 2
    if len(history) > max_msgs:
        history = [history[0]] + history[-(max_msgs - 1):]

    session["chat_history"] = history
    return jsonify({"reply": reply})


@app.route('/api/chat/reset', methods=['POST'])
def chat_reset():
    session.pop("chat_history", None)
    return jsonify({"status": "ok"})


# --- Feature 3: NL2Function planner ---
@app.route('/api/plan', methods=['POST'])
@limiter.limit("20 per minute")
def plan():
    if _planner is None:
        return jsonify({"error": "AI not configured"}), 503
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    query = data.get("query", "")
    if not isinstance(query, str) or not query.strip():
        return jsonify({"error": "query must be a non-empty string"}), 400

    intent = _planner.parse(query.strip())
    func = intent.get("function")
    params = intent.get("params", {})

    if not func:
        return jsonify({"error": "I didn't understand that. Try: 'Track ISS over Tokyo' or 'FSPL at 2.4 GHz, 500 km'"}), 422

    if func in ("track", "find_events"):
        city = params.get("city", "")
        lat = params.get("lat")
        lon = params.get("lon")

        if city and not (lat and lon):
            lat, lon, _ = _location_provider.get_lat_lon(str(city)[:100])
            if lat is None:
                return jsonify({"error": "Could not resolve the location."}), 400

        if lat is None or lon is None:
            return jsonify({"error": "Could not determine location. Provide a city name or coordinates."}), 400

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid coordinates"}), 400
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({"error": "Coordinates out of range"}), 400

        result, err = _compute_telemetry(lat, lon)
        if err:
            return jsonify({"error": err}), 500

        return jsonify({
            "function": func,
            "location": {"lat": lat, "lon": lon},
            "sat_name": result["name"],
            **result["telemetry"],
            "next_pass": result["next_pass"],
        })

    if func == "calculate_fspl":
        try:
            freq_hz = float(params.get("freq_hz", 0))
            dist_km = float(params.get("dist_km", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "freq_hz and dist_km must be numbers"}), 400
        if freq_hz <= 0 or dist_km <= 0:
            return jsonify({"error": "freq_hz and dist_km must be positive"}), 400
        fspl = LinkCalculator.calculate_fspl(freq_hz, dist_km)
        return jsonify({"function": "calculate_fspl", "fspl_db": f"{fspl:.2f} dB"})

    return jsonify({"error": "Unknown function"}), 422


# --- Feature 4: Alert feed ---
@app.route('/api/alerts')
def alerts():
    if _monitor is None:
        return jsonify([])
    return jsonify(_monitor.get_alerts())


# --- Feature 5: Mission briefing download ---
@app.route('/api/briefing')
@limiter.limit("5 per minute")
def briefing():
    if ai_assistant is None:
        return jsonify({"error": "AI not configured"}), 503
    with _telemetry_lock:
        snapshot = dict(_last_telemetry)
    if not snapshot:
        return jsonify({"error": "No telemetry data yet. Run a track first."}), 400
    try:
        report = ai_assistant.generate_briefing(snapshot)
    except Exception:
        app.logger.exception("Briefing generation failed")
        return jsonify({"error": "Briefing generation failed."}), 503

    return Response(
        report,
        mimetype='text/markdown',
        headers={'Content-Disposition': 'attachment; filename="mission_briefing.md"'},
    )


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
        .btn-primary { background: #0ea5e9; color: white; border: none; padding: 15px 30px; font-size: 1.1rem; border-radius: 50px; cursor: pointer; width: 100%; max-width: 300px; transition: background 0.2s; }
        .btn-primary:active { background: #0284c7; transform: scale(0.98); }
        .data-row { display: flex; justify-content: space-between; margin: 10px 0; border-bottom: 1px solid #334155; padding-bottom: 5px; }
        .label { color: #94a3b8; }
        .value { font-weight: bold; }
        #status { margin-top: 15px; color: #fbbf24; font-size: 0.9rem; }
        .ai-box { background: #0c4a6e; border-left: 4px solid #38bdf8; padding: 15px; text-align: left; font-size: 0.9rem; margin-top: 10px; border-radius: 4px; white-space: pre-wrap; min-height: 40px; }
        .hidden { display: none; }
        h3 { margin: 16px 0 8px; font-size: 1rem; color: #94a3b8; }
        /* Alert badge */
        #alert-badge { position: fixed; top: 12px; right: 12px; background: #ef4444; color: white; border-radius: 50px; padding: 6px 14px; font-size: 0.82rem; cursor: pointer; z-index: 100; display: none; }
        #alert-badge.show { display: block; }
        .alert-item { padding: 8px; border-radius: 6px; margin: 6px 0; font-size: 0.83rem; text-align: left; }
        .alert-WARNING { background: #431407; }
        .alert-CRITICAL { background: #7f1d1d; }
        /* Chat widget */
        .chat-section { text-align: left; margin-top: 15px; border-top: 1px solid #334155; padding-top: 15px; }
        #chat-messages { max-height: 200px; overflow-y: auto; margin-bottom: 10px; }
        .chat-msg-user { background: #1e3a5f; padding: 8px 12px; border-radius: 8px 8px 2px 8px; margin: 5px 0; font-size: 0.87rem; }
        .chat-msg-ai { background: #0c2a1e; padding: 8px 12px; border-radius: 2px 8px 8px 8px; margin: 5px 0; font-size: 0.87rem; }
        .chat-msg-error { background: #450a0a; padding: 8px 12px; border-radius: 4px; margin: 5px 0; font-size: 0.87rem; }
        .chat-input-row { display: flex; gap: 8px; }
        .chat-input-row input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 0.9rem; }
        .chat-input-row button { background: #0ea5e9; color: white; border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; }
        .btn-secondary { background: transparent; border: 1px solid #475569; color: #94a3b8; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; margin-top: 8px; }
        .btn-briefing { background: #065f46; color: #6ee7b7; border: 1px solid #059669; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 0.9rem; margin-top: 12px; width: 100%; }
        /* NL input */
        .nl-input { width: calc(100% - 24px); padding: 10px 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; font-size: 0.9rem; box-sizing: border-box; }
        /* Streaming cursor */
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        .cursor { display: inline-block; width: 7px; height: 1em; background: #38bdf8; animation: blink 1s step-end infinite; vertical-align: text-bottom; margin-left: 2px; }
    </style>
</head>
<body>
    <!-- Feature 4: Alert badge -->
    <button id="alert-badge" onclick="toggleAlerts()">&#9888; <span id="alert-count">0</span> Alert(s)</button>

    <h1>&#128752; PyOrbit-Link AI</h1>
    <p>Live Tracking &amp; Smart Link Analysis</p>

    <!-- Alert panel -->
    <div id="alert-panel" class="card hidden">
        <h3>Active Alerts</h3>
        <div id="alert-list"></div>
    </div>

    <!-- Feature 3: NL Planner -->
    <div class="card">
        <h3>Ask in Plain English</h3>
        <input type="text" class="nl-input" id="nl_query"
               placeholder='e.g. "Track ISS over Tokyo" or "FSPL at 12 GHz, 550 km"'>
        <button class="btn-primary" style="font-size:0.95rem;padding:10px 20px;margin-top:6px;"
                onclick="askPlainEnglish()">Ask AI</button>
        <pre id="nl_result" class="hidden"
             style="margin-top:8px;font-size:0.83rem;color:#94a3b8;text-align:left;white-space:pre-wrap;"></pre>
    </div>

    <!-- GPS / main action -->
    <div class="card">
        <button class="btn-primary" onclick="getLocation()">&#128205; Use My Location</button>
        <div id="status">Ready to track...</div>
        <button class="btn-briefing hidden" id="briefing-btn" onclick="downloadBriefing()">
            &#128196; Download Briefing
        </button>
    </div>

    <!-- Results -->
    <div id="results" class="card hidden">
        <h3>Live Telemetry</h3>
        <div class="data-row"><span class="label">Satellite</span><span class="value" id="sat_name">-</span></div>
        <div class="data-row"><span class="label">Azimuth</span><span class="value" id="azimuth">-</span></div>
        <div class="data-row"><span class="label">Elevation</span><span class="value" id="elevation">-</span></div>
        <div class="data-row"><span class="label">Distance</span><span class="value" id="distance">-</span></div>
        <div class="data-row"><span class="label">Link Loss (FSPL)</span><span class="value" id="fspl">-</span></div>

        <h3>&#129302; AI Mission Analysis</h3>
        <div class="ai-box">
            <span id="ai-text"></span><span id="ai-cursor" class="cursor hidden"></span>
        </div>

        <h3>Next Pass</h3>
        <div class="data-row"><span class="label">Rise Time</span><span class="value" id="pass_rise">-</span></div>
        <div class="data-row"><span class="label">Set Time</span><span class="value" id="pass_set">-</span></div>

        <!-- Feature 2: Chat widget -->
        <div class="chat-section hidden" id="chat-widget">
            <h3>&#128172; Ask Follow-up Questions</h3>
            <div id="chat-messages"></div>
            <div class="chat-input-row">
                <input type="text" id="chat-input" placeholder="Ask a follow-up question...">
                <button onclick="sendChat()">Send</button>
            </div>
            <button class="btn-secondary" onclick="resetChat()">New Chat</button>
        </div>
    </div>

    <script nonce="{{ nonce }}">
        var _eventSource = null;

        // Feature 4: Alert polling — uses DOM methods to avoid innerHTML with user data
        function pollAlerts() {
            fetch('/api/alerts').then(function(r) { return r.json(); }).then(function(alerts) {
                if (!alerts || alerts.length === 0) return;
                document.getElementById('alert-badge').classList.add('show');
                document.getElementById('alert-count').textContent = String(alerts.length);
                var list = document.getElementById('alert-list');
                while (list.firstChild) { list.removeChild(list.firstChild); }
                alerts.slice(0, 5).forEach(function(a) {
                    var item = document.createElement('div');
                    item.className = 'alert-item alert-' + (a.status === 'CRITICAL' ? 'CRITICAL' : 'WARNING');
                    var strong = document.createElement('strong');
                    strong.textContent = a.status || '';
                    item.appendChild(strong);
                    item.appendChild(document.createTextNode(' \u2014 ' + new Date(a.timestamp).toLocaleTimeString()));
                    var small = document.createElement('div');
                    small.style.fontSize = '0.8rem';
                    small.style.marginTop = '3px';
                    small.textContent = a.message || '';
                    item.appendChild(small);
                    list.appendChild(item);
                });
            }).catch(function() {});
        }
        setInterval(pollAlerts, 10000);
        pollAlerts();

        function toggleAlerts() {
            document.getElementById('alert-panel').classList.toggle('hidden');
        }

        // Feature 1: Streaming via EventSource
        function getLocation() {
            var status = document.getElementById('status');
            if (!navigator.geolocation) { status.textContent = "Geolocation not supported"; return; }
            status.textContent = "Acquiring GPS Signal...";
            navigator.geolocation.getCurrentPosition(startStream, function() {
                status.textContent = "Unable to retrieve your location";
            });
        }

        function startStream(position) {
            var lat = position.coords.latitude;
            var lon = position.coords.longitude;
            var status = document.getElementById('status');
            status.textContent = "GPS Locked: " + lat.toFixed(4) + ", " + lon.toFixed(4) + " \u2014 Streaming...";

            if (_eventSource) { _eventSource.close(); }
            document.getElementById('ai-text').textContent = '';
            document.getElementById('ai-cursor').classList.remove('hidden');

            _eventSource = new EventSource('/api/track/stream?lat=' + lat + '&lon=' + lon);

            _eventSource.addEventListener('telemetry', function(e) {
                var d = JSON.parse(e.data);
                document.getElementById('results').classList.remove('hidden');
                document.getElementById('sat_name').textContent = d.sat_name || '-';
                document.getElementById('azimuth').textContent = d.azimuth || '-';
                document.getElementById('elevation').textContent = d.elevation || '-';
                document.getElementById('distance').textContent = d.distance || '-';
                document.getElementById('fspl').textContent = d.fspl_db || '-';
                if (d.next_pass) {
                    document.getElementById('pass_rise').textContent = new Date(d.next_pass.Rise).toLocaleTimeString();
                    document.getElementById('pass_set').textContent = new Date(d.next_pass.Set).toLocaleTimeString();
                } else {
                    document.getElementById('pass_rise').textContent = "None soon";
                    document.getElementById('pass_set').textContent = "-";
                }
            });

            _eventSource.onmessage = function(e) {
                var token = JSON.parse(e.data);
                document.getElementById('ai-text').textContent += token;
            };

            _eventSource.addEventListener('done', function() {
                _eventSource.close();
                document.getElementById('ai-cursor').classList.add('hidden');
                document.getElementById('briefing-btn').classList.remove('hidden');
                document.getElementById('chat-widget').classList.remove('hidden');
                status.textContent = "Tracking Complete";
            });

            _eventSource.onerror = function() {
                _eventSource.close();
                document.getElementById('ai-cursor').classList.add('hidden');
                status.textContent = "Stream error \u2014 please retry";
            };
        }

        // Feature 5: Briefing download
        function downloadBriefing() { window.location.href = '/api/briefing'; }

        // Feature 2: Chat — uses createElement + textContent to avoid XSS
        function appendChatMsg(text, cssClass) {
            var msgList = document.getElementById('chat-messages');
            var div = document.createElement('div');
            div.className = cssClass;
            div.textContent = text;
            msgList.appendChild(div);
            msgList.scrollTop = msgList.scrollHeight;
        }

        function sendChat() {
            var input = document.getElementById('chat-input');
            var msg = input.value.trim();
            if (!msg) return;
            input.value = '';
            appendChatMsg(msg, 'chat-msg-user');

            fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: msg})
            }).then(function(r) { return r.json(); }).then(function(data) {
                appendChatMsg(data.reply || data.error || 'No response', data.reply ? 'chat-msg-ai' : 'chat-msg-error');
            }).catch(function() {
                appendChatMsg('Error \u2014 please retry.', 'chat-msg-error');
            });
        }

        function resetChat() {
            fetch('/api/chat/reset', {method: 'POST'}).then(function() {
                var msgList = document.getElementById('chat-messages');
                while (msgList.firstChild) { msgList.removeChild(msgList.firstChild); }
            });
        }

        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('chat-input').addEventListener('keydown', function(e) {
                if (e.key === 'Enter') sendChat();
            });
            document.getElementById('nl_query').addEventListener('keydown', function(e) {
                if (e.key === 'Enter') askPlainEnglish();
            });
        });

        // Feature 3: NL Planner
        function askPlainEnglish() {
            var query = document.getElementById('nl_query').value.trim();
            var result = document.getElementById('nl_result');
            if (!query) return;
            result.textContent = 'Processing...';
            result.classList.remove('hidden');

            fetch('/api/plan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            }).then(function(r) { return r.json(); }).then(function(data) {
                result.textContent = data.error ? data.error : JSON.stringify(data, null, 2);
            }).catch(function() { result.textContent = 'Request failed.'; });
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    app.run(host=host, port=port, debug=debug)
