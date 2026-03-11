from flask import Flask, render_template_string, jsonify, request
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to import pyorbit_link
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyorbit_link.tracker import SatTracker
from pyorbit_link.api import CelesTrakAPI
from pyorbit_link.calculator import LinkCalculator

app = Flask(__name__)

# Cache TLE data (fetch once per server start for efficiency)
TLE_CACHE = CelesTrakAPI.get_tle_by_norad_id(25544)  # ISS (NORAD 25544)

@app.route('/')
def home():
    """Renders the Mobile UI."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/track', methods=['POST'])
def track_iss():
    """API Endpoint: Receives GPS coordinates, returns next pass."""
    data = request.json
    lat = float(data.get('latitude'))
    lon = float(data.get('longitude'))
    
    if not TLE_CACHE:
        return jsonify({"error": "Could not fetch TLE data."}), 500

    name, l1, l2 = TLE_CACHE
    tracker = SatTracker(l1, l2, name)
    
    # Calculate current position (Az/El/Range)
    az, el, dist_km = tracker.get_aer(lat, lon, alt_m=10.0)
    
    # Calculate Link Budget (2.4 GHz WiFi example)
    freq = 2.4e9
    fspl = LinkCalculator.calculate_fspl(freq, dist_km)
    
    # Find next pass
    passes = tracker.find_events(lat, lon, alt_m=10.0, duration_days=1)
    next_pass = passes[0] if passes else None
    
    return jsonify({
        "sat_name": name,
        "azimuth": f"{az:.2f}°",
        "elevation": f"{el:.2f}°",
        "distance": f"{dist_km:.2f} km",
        "fspl_db": f"{fspl:.2f} dB",
        "next_pass": next_pass
    })

# --- Mobile HTML/JS Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>PyOrbit-Link Mobile</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f1f5f9; text-align: center; padding: 20px; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; margin: 15px auto; max-width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h1 { font-size: 1.5rem; margin-bottom: 10px; color: #38bdf8; }
        button { background: #0ea5e9; color: white; border: none; padding: 15px 30px; font-size: 1.1rem; border-radius: 50px; cursor: pointer; width: 100%; max-width: 300px; transition: background 0.2s; }
        button:active { background: #0284c7; transform: scale(0.98); }
        .data-row { display: flex; justify-content: space-between; margin: 10px 0; border-bottom: 1px solid #334155; padding-bottom: 5px; }
        .label { color: #94a3b8; }
        .value { font-weight: bold; }
        #status { margin-top: 15px; color: #fbbf24; font-size: 0.9rem; }
    </style>
</head>
<body>
    <h1>🛰️ PyOrbit-Link Mobile</h1>
    <p>Track the ISS from your exact GPS location.</p>
    
    <div class="card">
        <button onclick="getLocation()">📍 Use My Location</button>
        <div id="status">Ready to track...</div>
    </div>

    <div id="results" class="card" style="display:none;">
        <h3>Live Telemetry</h3>
        <div class="data-row"><span class="label">Satellite</span><span class="value" id="sat_name">-</span></div>
        <div class="data-row"><span class="label">Azimuth</span><span class="value" id="azimuth">-</span></div>
        <div class="data-row"><span class="label">Elevation</span><span class="value" id="elevation">-</span></div>
        <div class="data-row"><span class="label">Distance</span><span class="value" id="distance">-</span></div>
        <div class="data-row"><span class="label">Link Loss (FSPL)</span><span class="value" id="fspl">-</span></div>
        
        <h3>Next Pass</h3>
        <div class="data-row"><span class="label">Rise Time</span><span class="value" id="pass_rise">-</span></div>
        <div class="data-row"><span class="label">Set Time</span><span class="value" id="pass_set">-</span></div>
    </div>

    <script>
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
                document.getElementById('results').style.display = 'block';
                document.getElementById('sat_name').textContent = data.sat_name;
                document.getElementById('azimuth').textContent = data.azimuth;
                document.getElementById('elevation').textContent = data.elevation;
                document.getElementById('distance').textContent = data.distance;
                document.getElementById('fspl').textContent = data.fspl_db;
                
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
    # Run on all interfaces (0.0.0.0) so it's accessible on your local network
    app.run(host='0.0.0.0', port=5000, debug=True)
