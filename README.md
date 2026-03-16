# 🛰️ LEO Orbital Systems (LOS) — Monorepo

**LOS** is a monorepo containing two complementary Python projects for modelling and analysing Low Earth Orbit (LEO) satellite systems. Together they cover the full stack — from orbital mechanics and RF link budgeting to network simulation and AI-powered diagnostics.

Both projects demonstrate core technical competencies for high-speed, low-latency satellite constellations like **Amazon Project Kuiper** and **SpaceX Starlink**.

---

## 📦 Projects

### 🛰️ [PyOrbit-Link](./PyOrbit-Link) — LEO Satellite Tracker & RF Link Budget Toolkit
> `github.com/hoomanp/PyOrbit-Link`

A real-time satellite tracking and RF engineering toolkit.

- Live TLE ingestion from CelesTrak by NORAD ID
- Orbit propagation via Skyfield (`EarthSatellite` / SGP4)
- RF link budget: FSPL, CNR, Doppler shift, antenna gain, atmospheric attenuation
- Polar sky-plot visualizer (Matplotlib)
- Flask mobile client with HTML5 GPS and RAG-enabled AI mission analysis

**[→ View PyOrbit-Link README](./PyOrbit-Link/README.md)**

---

### 🌐 [ConstellaSim](./ConstellaSim) — LEO Network Topology Simulator
> `github.com/hoomanp/ConstellaSim`

A discrete-event simulator for packet-level LEO constellation networking.

- SimPy-based event engine with Dijkstra routing (NetworkX)
- ISL and GSL link modelling with congestion, buffer overflow, and handover logic
- End-to-end latency, packet loss, and hop count analytics
- Flask mobile client with GPS-based simulation setup and RAG-enabled AI network analysis

**[→ View ConstellaSim README](./ConstellaSim/README.md)**

---

## 🏗️ Repository Structure

```
LOS/
├── PyOrbit-Link/               # Satellite tracker & RF toolkit (own git remote)
│   ├── pyorbit_link/           # Core library modules
│   │   ├── tracker.py          # Orbit propagation & AER computation
│   │   ├── calculator.py       # RF link budget formulas
│   │   ├── api.py              # CelesTrak TLE fetcher
│   │   ├── visualizer.py       # Polar sky-plot renderer
│   │   ├── utils.py            # ZIP/city geocoding
│   │   └── llm.py              # RAG-enabled AI assistant
│   ├── mobile_client/app.py    # Flask REST API + mobile web UI
│   ├── examples/               # Runnable demos
│   ├── knowledge_base/         # ITU-R standards docs for RAG
│   └── requirements.txt
│
├── ConstellaSim/               # LEO network simulator (own git remote)
│   ├── constellasim/           # Core library modules
│   │   ├── engine.py           # Discrete-event simulation engine
│   │   ├── node.py             # Satellite & GroundStation node classes
│   │   ├── utils.py            # Geocoding utilities
│   │   └── llm.py              # RAG-enabled AI network analyst
│   ├── mobile_client/app.py    # Flask REST API + mobile web UI
│   ├── examples/               # Runnable demos
│   ├── knowledge_base/         # LEO networking standards docs for RAG
│   └── requirements.txt
│
└── README.md                   # This file
```

---

## 🚀 Quick Start

Each project has its own `requirements.txt` and can be installed independently.

**PyOrbit-Link:**
```bash
cd PyOrbit-Link
pip install -r requirements.txt
python3 -m examples.advanced_features
```

**ConstellaSim:**
```bash
cd ConstellaSim
pip install -r requirements.txt
python3 -m examples.multi_hop_demo
```

---

## ☁️ Multi-Cloud AI Support

Both projects share the same modular RAG architecture (`llm.py`). Switch providers via environment variable:

| Project | Variable | Providers |
|---|---|---|
| PyOrbit-Link | `SAT_AI_PROVIDER` | `google` (default), `azure`, `amazon` |
| ConstellaSim | `NETWORK_AI_PROVIDER` | `google` (default), `azure`, `amazon` |

---

## 📄 License
Distributed under the MIT License.

## 🤝 Contact
**Hooman P.** - [GitHub](https://github.com/hoomanp)
