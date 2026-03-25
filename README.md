# PyOrbit-Link: LEO Satellite Tracker, RF Link Budget Toolkit & Native iOS App

**PyOrbit-Link** is a full-stack satellite communications platform combining a Python/Flask backend for real-time LEO orbital mechanics with a production-grade **native iOS app** built in SwiftUI. It bridges orbital mechanics, RF engineering, and mobile UX into a single deployable system.

---

## What's Inside

| Layer | Technology | Purpose |
|---|---|---|
| `pyorbit_link/` | Python 3.9+, Skyfield | Orbital propagation (SGP4), AER, FSPL, Doppler |
| `mobile_client/app.py` | Flask, SSE | REST + Server-Sent Events API (port 5001) |
| `iOS/PyOrbitLink/` | SwiftUI, iOS 17+ | Native iPhone app, App Store ready |

---

## Key Features

### Orbital Domain
- **CelesTrak TLE Fetch:** Real-time Two-Line Elements via NORAD ID (ISS default: 25544).
- **SGP4 Propagation:** High-fidelity pass prediction with Skyfield's `EarthSatellite`.
- **AER Computation:** Azimuth, Elevation, and Range for any ground observer.
- **Geocoding:** ZIP code, city name, or GPS coordinates via Geopy/Nominatim.

### RF & Link Budget
- **FSPL Model:** Free-space path loss at configurable frequency (default 437.525 MHz UHF).
- **Doppler Shift:** Real-time ±kHz frequency correction at 7.5 km/s orbital velocity.
- **Atmospheric Attenuation:** ITU-R P.618 rain fade and gaseous loss (Ka/V-band).
- **CNR / Link Budget:** Carrier-to-noise ratio and antenna gain (dBi) modeling.

### AI / RAG Mission Assistant (5 Features)
1. **Streaming Analysis** — SSE endpoint streams AI commentary token-by-token as telemetry arrives.
2. **Multi-Turn Chat** — Contextual follow-up questions about the current pass and link budget.
3. **NL2Function Planner** — Natural language commands resolve to simulation actions ("Track ISS from Paris").
4. **Anomaly Alerts** — Background monitor flags degraded link margins (WARNING / CRITICAL severity).
5. **Network Briefing** — Downloadable Markdown report grounded in `knowledge_base/` ITU-R documents.

Providers: **Google Gemini 1.5 Flash**, **Azure OpenAI (GPT-4 Turbo)**, **Amazon Bedrock (Claude 3)**.

### Native iOS App — PyOrbitLink
A fully App-Store-ready SwiftUI application connecting to the Flask backend over LAN or internet.

**5 Tabs:**

| Tab | Description |
|---|---|
| **Live Track** | Real-time SSE satellite map (MapKit iOS 17), AER chart, Sky View polar plot, Link Budget chart |
| **Signal Monitor** | Device GPS accuracy, cellular radio tech (5G NR/LTE/WCDMA/GSM), Wi-Fi vs cellular, rolling history |
| **AI Chat** | Multi-turn streaming conversation with the Mission Assistant |
| **Mission Planner** | Natural-language mission planning via the NL2Function endpoint |
| **Anomaly Alerts** | Polled alert feed with badge count and WARNING/CRITICAL classification |

**Device Sensors:**
- `CoreLocation` — GPS coordinates, accuracy, altitude, heading
- `CoreTelephony` — Radio access technology (5G NR / LTE / WCDMA / GSM)
- `NWPathMonitor` — Wi-Fi vs. cellular reachability
- Swift Charts — AER time series, polar sky view, link budget waterfall

**Demo Mode — ZIP 91356-4144, Tarzana, CA:**
When GPS is unavailable (e.g. simulator), the app pre-loads a 15-point ISS pass arc:

| Metric | Value |
|---|---|
| Observer | 34.1675°N, 118.5504°W (Tarzana, CA) |
| Pass direction | SW (220°) → peak W (305°) → NW (351°) |
| Peak elevation | 63.2° at 469 km range |
| Peak FSPL | 138.7 dB at 437.525 MHz |
| Horizon FSPL | 148.5 dB (elevation 5.4°) |

---

## Architecture

```
PyOrbit-Link/
├── pyorbit_link/
│   ├── tracker.py          # SGP4 propagation, AER, pass prediction
│   ├── calculator.py       # FSPL, Doppler, CNR, atmospheric loss
│   ├── visualizer.py       # Matplotlib polar sky view
│   ├── api.py              # CelesTrak TLE fetch (timeout=10s)
│   ├── utils.py            # Geocoding (Geopy/Nominatim)
│   └── llm.py              # RAG AI assistant (Google/Azure/Bedrock)
├── mobile_client/
│   └── app.py              # Flask REST + SSE API (port 5001)
├── knowledge_base/         # ITU-R standards for RAG grounding
├── examples/               # CLI demos
└── iOS/
    └── PyOrbitLink/
        ├── Models/         # Telemetry, SignalReading, SampleData (demo pass)
        ├── Services/       # LocationService, SignalMonitorService
        ├── ViewModels/     # LiveTrack, Signal, Chat, Planner, Alerts
        ├── Views/          # 5 SwiftUI tab views
        ├── Charts/         # AERChart, SignalChart, LinkBudgetChart
        └── Components/     # SatelliteMapView, SignalGauge, StreamingText
```

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/track` | One-shot telemetry for given lat/lon |
| `GET` | `/api/track/stream` | SSE: telemetry frame + streaming AI analysis |
| `POST` | `/api/chat` | Multi-turn AI conversation |
| `POST` | `/api/chat/reset` | Clear session history |
| `POST` | `/api/plan` | NL2Function mission planning |
| `GET` | `/api/alerts` | Anomaly alert feed (JSON array) |
| `GET` | `/api/briefing` | Download Markdown network briefing |

---

## Installation

```bash
git clone https://github.com/hoomanp/PyOrbit-Link.git
cd PyOrbit-Link
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Start the Backend

```bash
export FLASK_SECRET_KEY=your-secret-key   # required
export GOOGLE_API_KEY=your-key             # or AZURE_OPENAI_KEY / AWS creds
export PORT=5001
python3 mobile_client/app.py
```

Web UI available at `http://localhost:5001`. Point the iOS app to your machine's LAN IP on the same port.

### Build the iOS App

Requirements: Xcode 15+, iOS 17.0+ deployment target.

**Simulator (no signing):**
```bash
cd iOS
xcodebuild -project PyOrbitLink.xcodeproj -target PyOrbitLink \
           -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO ONLY_ACTIVE_ARCH=NO
xcrun simctl install booted build/Debug-iphonesimulator/PyOrbitLink.app
xcrun simctl launch booted com.pyorbitlink.app
```

**Device / App Store:**
```bash
xcodebuild -project PyOrbitLink.xcodeproj -target PyOrbitLink \
           -configuration Release -sdk iphoneos \
           CODE_SIGNING_IDENTITY="iPhone Distribution: Your Name" \
           DEVELOPMENT_TEAM=YOUR_TEAM_ID
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | — | **Required.** Cryptographic session key |
| `PORT` | `5001` | Flask server port |
| `SAT_AI_PROVIDER` | `google` | AI provider: `google`, `azure`, `amazon` |
| `GOOGLE_API_KEY` | — | Google Gemini 1.5 Flash API key |
| `AZURE_OPENAI_KEY` | — | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_DEPLOYMENT_NAME` | `gpt-4-turbo` | Azure deployment name |
| `ANOMALY_MONITOR` | `false` | Enable background alert polling thread |
| `FLASK_DEBUG` | `false` | Development mode (never `true` in production) |

---

## Tech Stack

**Backend:** Python 3.9+, Flask, Skyfield (SGP4), Geopy, flask-limiter, python-dotenv

**AI:** Google Generative AI (Gemini 1.5 Flash), OpenAI SDK (Azure), Boto3 (Amazon Bedrock)

**iOS:** Swift 5.9, SwiftUI (iOS 17+), Swift Charts, MapKit (iOS 17 API), CoreLocation, CoreTelephony, NWPathMonitor, URLSession async/await

---

## Changelog

### v1.3 — Native iOS App + Demo Mode (2026-03)
- Full SwiftUI native iOS app (`iOS/PyOrbitLink/`) — App Store ready, iOS 17.0+
- 5 tabs: Live Track, Signal Monitor, AI Chat, Mission Planner, Anomaly Alerts
- MapKit satellite map with Observer and ISS markers (real-time from backend)
- Swift Charts: AER time series, polar sky view, link budget waterfall chart
- Device sensors: CoreLocation GPS, CoreTelephony radio tech, NWPathMonitor
- Demo mode with pre-computed ISS pass for ZIP 91356-4144 (Tarzana, CA)
- Flexible JSON decoder handling string-formatted values (`"189.99°"`, `"8607.98 km"`)
- Backend key mapping: `distance` → range, `fspl_db` → fspl
- Fixed all Xcode 15 build issues (AxisValueLabel, gradient type, symbolEffect, MapKit iOS 17)

### v1.2 — 5 AI Features + Security Audit (2026-02)
- Streaming SSE AI analysis, multi-turn chat, NL2Function planner, anomaly monitor, briefing download
- 18 security findings fixed: CSP nonces, rate limiting, path traversal guards, prompt injection sanitisation
- `FLASK_SECRET_KEY` now required at startup; port moved to 5001

### v1.1 — Backend Fixes
- Fixed `EarthSatellite()` initialisation, `total_link_budget()` CNR return, division-by-zero at 0° elevation
- Added `timeout=10` to CelesTrak requests; `FLASK_DEBUG` env var (default `false`)

---

## License
MIT License.

## Contact
**Hooman P.** — [GitHub](https://github.com/hoomanp)
