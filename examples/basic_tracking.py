from pyorbit_link.tracker import SatTracker
from pyorbit_link.calculator import LinkCalculator
import datetime

# ISS (International Space Station) TLE data (Example)
TLE_1 = "1 25544U 98067A   24068.52445602  .00015569  00000-0  27848-3 0  9997"
TLE_2 = "2 25544  51.6416  20.0863 0004782  56.0968  51.1557 15.49528646443103"

def main():
    # 1. Initialize Tracker
    tracker = SatTracker(TLE_1, TLE_2, "ISS")
    
    # 2. Find passes for a Ground Station (Example: El Segundo, CA)
    LAT, LON, ALT = 33.9192, -118.4165, 30.0
    print(f"--- Finding ISS passes for El Segundo, CA (Lat: {LAT}, Lon: {LON}) ---")
    passes = tracker.find_events(LAT, LON, ALT, duration_days=1) # Note: fix tracker.py method call
    for p in passes:
        print(f"Pass: Rise: {p.get('Rise')}, Set: {p.get('Set')}")

    # 3. Calculate RF Parameters for a theoretical 2.4GHz link
    FREQ = 2.4e9 # 2.4 GHz
    DISTANCE = 420.0 # km (approx ISS altitude)
    VELOCITY_REL = 7660.0 # m/s (approx ISS velocity)
    
    fspl = LinkCalculator.calculate_fspl(FREQ, DISTANCE)
    doppler = LinkCalculator.calculate_doppler_shift(FREQ, VELOCITY_REL)
    
    print("\n--- RF Link Stats (Theoretical) ---")
    print(f"Frequency: {FREQ/1e9} GHz")
    print(f"Distance: {DISTANCE} km")
    print(f"Free-Space Path Loss: {fspl:.2f} dB")
    print(f"Doppler Shift: {doppler/1e3:.2f} kHz")

if __name__ == "__main__":
    main()
