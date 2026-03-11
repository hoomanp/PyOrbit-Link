# Developer Guide: PyOrbit-Link

Welcome to the **PyOrbit-Link** code guide! This document explains how the code is structured and how you can extend it for your own satellite experiments.

## 🏗️ Project Architecture

The project is split into two logical domains:

1.  **`tracker.py` (Orbital Domain):** Handles the "where" and "when." It uses the `Skyfield` library to propagate satellite orbits from TLE data.
2.  **`calculator.py` (RF Domain):** Handles the "how strong." It takes physical inputs (distance, frequency, velocity) and calculates the telecommunications metrics.

This separation allows you to swap out the orbital propagator (e.g., if you want to use `Astropy` or `Orekit`) without breaking the RF math.

## 🐍 Python Best Practices

- **Object-Oriented Design:** `SatTracker` and `LinkCalculator` are designed to be reusable in larger automation frameworks.
- **Static Methods:** The `LinkCalculator` uses static methods because the RF formulas (like FSPL) are stateless mathematical operations.
- **Type Hinting:** (Coming soon) We aim to use Python's `typing` module for better IDE support.

## 🔭 How to Extend This Project

### 1. Add Real-time TLE Loading
Currently, the user must provide the TLE string. You could add a module that fetches the latest TLEs from **CelesTrak** or **Space-Track.org** using the `requests` library.

### 2. Visualize the Ground Track
Integrate with `Matplotlib` or `Plotly` to create a world map showing the satellite's path across the Earth.

### 3. Hardware-in-the-loop (HIL)
If you have access to an SDR (Software Defined Radio) like an RTL-SDR or HackRF, you can use the Doppler output from this code to dynamically adjust your radio's center frequency!

## 🧪 Running Tests
We use `pytest` for unit testing. To run the tests:

```bash
cd PyOrbit-Link
pytest tests/
```

*(Note: Don't forget to add a simple test file in the `tests/` directory to get started!)*
