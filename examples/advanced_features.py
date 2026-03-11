from pyorbit_link.tracker import SatTracker
from pyorbit_link.calculator import LinkCalculator
from pyorbit_link.api import CelesTrakAPI
from pyorbit_link.visualizer import SatVisualizer
from pyorbit_link.utils import LocationProvider
import datetime

def main():
    # 1. Fetch Latest TLE for ISS (NORAD 25544)
    print("--- 🛰️ Fetching Real-time TLE from CelesTrak ---")
    tle_data = CelesTrakAPI.get_tle_by_norad_id(25544)
    if not tle_data:
        return
    
    name, l1, l2 = tle_data
    tracker = SatTracker(l1, l2, name)
    
    # 2. Get User Location (ZIP or City)
    loc_input = input("Enter your ZIP code or City (e.g., 90210 or 'Los Angeles'): ")
    lp = LocationProvider()
    LAT, LON, address = lp.get_lat_lon(loc_input)
    
    if not LAT:
        print("❌ Could not resolve location. Using default (El Segundo, CA).")
        LAT, LON, ALT = 33.9192, -118.4165, 30.0
    else:
        print(f"✅ Found: {address} ({LAT}, {LON})")
        ALT = 30.0
    
    # 3. Calculate Antenna Gain for a 1.2m Ka-band dish (30GHz)
    FREQ = 30e9
    GAIN = LinkCalculator.calculate_antenna_gain(1.2, FREQ)
    print(f"Antenna Gain (1.2m @ 30GHz): {GAIN:.2f} dBi")
    
    # 4. Get Current Position and Link Stats
    az, el, dist = tracker.get_aer(LAT, LON, ALT)
    atm_loss = LinkCalculator.calculate_atmospheric_loss(el, FREQ/1e9, rain_rate_mm_hr=5.0)
    
    print(f"\n--- 📡 Current Status for {name} ---")
    print(f"Azimuth: {az:.2f}°, Elevation: {el:.2f}°")
    print(f"Distance: {dist:.2f} km")
    print(f"Atmospheric Loss (Rainy): {atm_loss:.2f} dB")
    
    # 5. Export JSON Telemetry
    telemetry = {
        "sat_name": name,
        "timestamp": str(datetime.datetime.now()),
        "azimuth": az,
        "elevation": el,
        "distance_km": dist,
        "antenna_gain_dbi": GAIN,
        "atmospheric_loss_db": atm_loss
    }
    LinkCalculator.export_results_json(telemetry, "iss_live_telemetry.json")

if __name__ == "__main__":
    main()
