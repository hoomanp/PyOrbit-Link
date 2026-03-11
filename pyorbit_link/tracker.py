from skyfield.api import Topos, load
from datetime import datetime, timedelta

class SatTracker:
    def __init__(self, tle_line1, tle_line2, sat_name="SAT"):
        self.ts = load.timescale()
        self.planets = load('de421.bsp')
        self.sat = load.tle_legacy(tle_line1, tle_line2, sat_name)

    def find_events(self, lat, lon, alt_m, duration_days=1):
        """Find when the satellite is above the horizon for a ground observer."""
        observer = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt_m)
        t0 = self.ts.now()
        t1 = self.ts.from_datetime(t0.utc_datetime() + timedelta(days=duration_days))
        
        # Find rising, culmination, and setting times
        times, events = self.sat.find_events(observer, t0, t1, altitude_degrees=10.0)
        
        passes = []
        current_pass = {}
        for t, event in zip(times, events):
            name = ('Rise', 'Culmination', 'Set')[event]
            current_pass[name] = t.utc_iso()
            if name == 'Set':
                passes.append(current_pass)
                current_pass = {}
        return passes

    def get_aer(self, lat, lon, alt_m, time_obj=None):
        """Returns Azimuth, Elevation, and Range (Distance) from a ground observer."""
        observer = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt_m)
        t = self.ts.now() if not time_obj else self.ts.from_datetime(time_obj)
        difference = self.sat - observer
        topocentric = difference.at(t)
        alt, az, distance = topocentric.altaz()
        return az.degrees, alt.degrees, distance.km
