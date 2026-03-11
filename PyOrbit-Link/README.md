# PyOrbit-Link: LEO Satellite Visibility & RF Link Calculator

**PyOrbit-Link** is a lightweight Python toolkit designed for calculating satellite visibility and RF link performance for Low Earth Orbit (LEO) constellations. 

This project was inspired by the technical requirements for High-Speed, Low-Latency satellite communications systems (like Project Kuiper and Starlink).

## 🚀 Features

- **Satellite Pass Tracking:** Predict "Visibility Windows" from any ground station using TLE (Two-Line Element) data.
- **RF Link Budgeting:** Calculate Free-Space Path Loss (FSPL) and Carrier-to-Noise Ratio (CNR).
- **Doppler Shift Analysis:** Model the frequency shift of a moving satellite relative to a ground observer.
- **Pythonic Interface:** Built on top of `Skyfield` for high-precision astronomy calculations.

## 🛠️ Installation

```bash
git clone https://github.com/YOUR_USERNAME/PyOrbit-Link.git
cd PyOrbit-Link
pip install -r requirements.txt
```

## 📊 Quick Start

Check the `examples/` directory for a full demonstration tracking the ISS.

```python
from pyorbit_link.tracker import SatTracker
from pyorbit_link.calculator import LinkCalculator

# Track a satellite using TLE lines
tracker = SatTracker(TLE_1, TLE_2, "MY_SAT")
passes = tracker.find_events(lat=33.9, lon=-118.4, alt_m=30)

# Calculate Doppler for a 2.4GHz link at 7.6 km/s
doppler = LinkCalculator.calculate_doppler_shift(2.4e9, 7660)
print(f"Doppler Shift: {doppler/1e3} kHz")
```

## 🛰️ Technical Context

For LEO satellites, the relative velocity can exceed 7.5 km/s, causing significant **Doppler Shift** that must be compensated for in the ground station's transceiver. Additionally, because the distance to the satellite changes rapidly during a pass, the **Link Budget** must be dynamically calculated to ensure the signal remains above the noise floor.

## 🚧 Roadmap

- [ ] Support for multi-satellite constellation simulation.
- [ ] Integration with real-time TLE APIs (e.g., CelesTrak).
- [ ] Atmospheric attenuation models (Rain Fade/ITU-R P.618).

## 📄 License
MIT
