# 🛰️ PyOrbit-Link: LEO Satellite Tracker & RF Link Budget Toolkit

**PyOrbit-Link** is a comprehensive Python-based suite designed for the mission-critical analysis of Low Earth Orbit (LEO) satellite communications. Developed with an emphasis on systems integration, it bridges the gap between orbital mechanics and telecommunications engineering.

This project demonstrates the core technical competencies required for high-speed, low-latency satellite constellations like **Amazon Project Kuiper** and **SpaceX Starlink**.

---

## 🚀 Key Features

### 🌌 Orbital Domain
- **CelesTrak API Integration:** Automatically fetches high-precision, real-time Two-Line Elements (TLEs) via NORAD IDs.
- **Precision Tracking:** High-fidelity orbit propagation using the `Skyfield` library (SGP4 model).
- **Global Geocoding:** Integrated `geopy` support allowing users to track passes from a ZIP code, city name, or precise GPS coordinates.

### 📡 RF & Telecommunications Domain
- **Dynamic Doppler Analysis:** Real-time calculation of frequency shifts (±kHz) caused by 7.5 km/s satellite velocities.
- **Advanced Link Budgeting:** Models Free-Space Path Loss (FSPL), Carrier-to-Noise Ratio (CNR), and Antenna Gain (dBi) based on aperture diameter and frequency.
- **Atmospheric Attenuation:** Simplified ITU-R P.618 models for Rain Fade and Gaseous absorption (critical for Ka-band/V-band links).
- **Polar Visualizer:** Radar-style Azimuth/Elevation plotting to visualize the satellite's path across the sky.

### 📱 Full-Stack Mobile & AI Integration
- **Flask-powered Mobile Client:** A cross-platform web interface optimized for iPhone and Android.
- **HTML5 Geolocation:** Uses your phone's native GPS to run "over-the-shoulder" tracking and link analysis from your exact physical location.
- **🤖 AI Mission Assistant:** Intelligent link analysis powered by **Azure OpenAI**, **Amazon Bedrock**, or **Google Gemini**. Automatically interprets link budget data to provide engineering recommendations and troubleshooting steps.

---

## ☁️ Multi-Cloud AI Support
This project features a unified AI wrapper (`llm.py`) that allows you to switch between the world's leading LLM providers with a single environment variable:
- **Amazon Bedrock:** Optimized for AWS-native satellite infrastructure.
- **Azure OpenAI:** High-reliability enterprise AI.
- **Google Gemini:** Advanced multimodal analysis.

## 🛠️ Tech Stack
- **Languages:** Python 3.9+
- **Orbital Propagation:** Skyfield, NumPy
- **API/Networking:** Requests, Flask (REST API)
- **Geocoding:** Geopy (Nominatim)
- **Visualization:** Matplotlib
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

1. **Start the Flask Server:**
   ```bash
   python3 mobile_client/app.py
   ```
2. **Access from Phone:**
   Open your mobile browser and navigate to `http://<YOUR_LAPTOP_IP>:5000`.
3. **Track:** Tap "Use My Location" to see live ISS telemetry relative to your position!

---

## 🔭 Technical Architecture
The project follows a modular **Systems Integration** pattern:
- `tracker.py`: Pure orbital mechanics and coordinate transformations.
- `calculator.py`: Physics-based RF formulas and link budgeting logic.
- `visualizer.py`: Data visualization layer.
- `api.py` / `utils.py`: Data acquisition and geocoding services.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

## 🤝 Contact
**Hooman P.** - [GitHub](https://github.com/hoomanp)
