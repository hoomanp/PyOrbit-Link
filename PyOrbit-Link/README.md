# 🛰️ PyOrbit-Link: LEO Satellite Tracker & RF Link Budget Toolkit

**PyOrbit-Link** is a comprehensive Python-based suite designed for the mission-critical analysis of Low Earth Orbit (LEO) satellite communications. Developed with an emphasis on systems integration, it bridges the gap between orbital mechanics and telecommunications engineering.

This project demonstrates the core technical competencies required for high-speed, low-latency satellite constellations like **Amazon Project Kuiper** and **SpaceX Starlink**.

---

## 🚀 Key Features

### 🌌 Orbital Domain
- **CelesTrak API Integration:** Automatically fetches high-precision, real-time Two-Line Elements (TLEs) via NORAD IDs.
- **Precision Tracking:** High-fidelity orbit propagation using the `Skyfield` library (`EarthSatellite` / SGP4 model).
- **Global Geocoding:** Integrated `geopy` support allowing users to track passes from a ZIP code, city name, or precise GPS coordinates.

### 📡 RF & Telecommunications Domain
- **Dynamic Doppler Analysis:** Real-time calculation of frequency shifts (±kHz) caused by 7.5 km/s satellite velocities.
- **Advanced Link Budgeting:** Models Free-Space Path Loss (FSPL), Carrier-to-Noise Ratio (CNR), and Antenna Gain (dBi) based on aperture diameter and frequency.
- **Atmospheric Attenuation:** Simplified ITU-R P.618 models for Rain Fade and Gaseous absorption (critical for Ka-band/V-band links). Elevation is clamped to a minimum of 1° to prevent invalid results at the horizon.
- **Polar Visualizer:** Radar-style Azimuth/Elevation plotting to visualize the satellite's path across the sky.

### 📱 Full-Stack Mobile & AI Integration
- **Flask-powered Mobile Client:** A cross-platform web interface optimized for iPhone and Android.
- **HTML5 Geolocation:** Uses your phone's native GPS to run "over-the-shoulder" tracking and link analysis from your exact physical location.
- **🤖 RAG-Enabled Mission Assistant:** Intelligent link analysis powered by **Azure OpenAI**, **Amazon Bedrock (Claude 3)**, or **Google Gemini (1.5 Flash)**.
- **📚 Grounded Knowledge Base:** Uses **Retrieval-Augmented Generation (RAG)** to "read" technical documents (like ITU-R standards) in the `knowledge_base/` folder. It provides engineering recommendations and flags "Mission Risks" based on actual satellite regulations.

---

## ☁️ Multi-Cloud & RAG Support
This project features a modular AI layer (`llm.py`) that utilizes the latest **Long-Context** windows and RAG architectures:
- **Grounded Analysis:** The AI automatically scans `knowledge_base/*.txt` to provide context-aware responses.
- **Provider Agnostic:** Switch between **Amazon Bedrock**, **Azure**, or **Google** via the `SAT_AI_PROVIDER` environment variable.

---

## 🛠️ Tech Stack
- **Languages:** Python 3.9+
- **Orbital Propagation:** Skyfield (`EarthSatellite` / SGP4), NumPy
- **API/Networking:** Requests, Flask (REST API)
- **Geocoding:** Geopy (Nominatim)
- **Visualization:** Matplotlib
- **AI / Multi-Cloud:** OpenAI SDK, Boto3 (AWS Bedrock), Google Generative AI
- **Configuration:** python-dotenv
- **Data Export:** JSON Telemetry Logging

---

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/hoomanp/PyOrbit-Link.git
   cd PyOrbit-Link
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Desktop Advanced Demo:**
   ```bash
   python3 -m examples.advanced_features
   ```

---

## 📱 Mobile Client Setup

To use the mobile client with your phone's GPS:

1. **Configure environment (optional):**
   ```bash
   export SAT_AI_PROVIDER=google   # or: azure, amazon
   export GOOGLE_API_KEY=your_key
   # FLASK_DEBUG defaults to false; set to true only for local development
   export FLASK_DEBUG=false
   ```

2. **Start the Flask Server:**
   ```bash
   python3 mobile_client/app.py
   ```

3. **Access from Phone:**
   Open your mobile browser and navigate to `http://<YOUR_LAPTOP_IP>:5000`.

4. **Track:** Tap "Use My Location" to see live ISS telemetry relative to your position!

---

## 🔭 Technical Architecture

The project follows a modular **Systems Integration** pattern:

| Module | Responsibility |
|---|---|
| `tracker.py` | Orbital mechanics using `EarthSatellite` (SGP4). Pass prediction and AER computation. |
| `calculator.py` | Physics-based RF formulas: FSPL, Doppler shift, antenna gain, atmospheric loss, and CNR link budget. |
| `visualizer.py` | Radar-style polar pass plotting via Matplotlib. |
| `api.py` | Live TLE acquisition from CelesTrak (with request timeout). |
| `utils.py` | ZIP/city-to-GPS geocoding via Geopy. |
| `llm.py` | RAG-enabled AI assistant; reads `knowledge_base/` and queries Azure / Bedrock / Gemini. |
| `mobile_client/app.py` | Flask REST API + mobile-optimized web UI. `SatTracker` is cached at startup for performance. |

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SAT_AI_PROVIDER` | `google` | AI provider: `google`, `azure`, or `amazon` |
| `GOOGLE_API_KEY` | — | API key for Google Gemini |
| `AZURE_OPENAI_KEY` | — | API key for Azure OpenAI |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_DEPLOYMENT_NAME` | `gpt-4-turbo` | Azure deployment name |
| `FLASK_DEBUG` | `false` | Set to `true` only for local development |

---

## 📋 Changelog

### Latest
- **Fix:** Replaced non-existent `load.tle_legacy()` with `EarthSatellite()` — tracker now initialises correctly.
- **Fix:** Removed unused `de421.bsp` planetary ephemeris load (eliminated a redundant ~17 MB download on startup).
- **Fix:** `total_link_budget()` was missing the CNR computation and `return` statement — it now correctly returns CNR in dB.
- **Fix:** `calculate_atmospheric_loss()` raised a division-by-zero error at 0° elevation — elevation is now clamped to a minimum of 1°.
- **Fix:** `get_aer()` now makes naive `datetime` objects UTC-aware before passing them to Skyfield.
- **Security:** Added `timeout=10` to CelesTrak `requests.get()` call to prevent indefinite hangs.
- **Security:** Flask `debug=True` replaced with `FLASK_DEBUG` environment variable (defaults to `false`).
- **Security:** Added full input validation and coordinate range checks on the `/api/track` endpoint.
- **Optimization:** `SatTracker` is now instantiated once at server startup and reused across all requests.
- **Optimization:** `kb_path` in `llm.py` is now resolved with `os.path.abspath()`.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

## 🤝 Contact
**Hooman P.** - [GitHub](https://github.com/hoomanp)
