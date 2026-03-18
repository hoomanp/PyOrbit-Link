from skyfield.api import Topos, load, EarthSatellite
from datetime import datetime, timedelta, timezone

class SatTracker:
    def __init__(self, tle_line1, tle_line2, sat_name="SAT"):
        self.ts = load.timescale()
        # Bug fix: load.tle_legacy() does not exist; use EarthSatellite directly.
        # Also removed unused self.planets = load('de421.bsp') (17MB download, never referenced).
        self.sat = EarthSatellite(tle_line1, tle_line2, sat_name, self.ts)

    def find_events(self, lat, lon, alt_m, duration_days=1):
        """Find when the satellite is above the horizon for a ground observer."""
        # L-4: validate inputs at the library boundary to catch bad values from any caller.
        if not (-90 <= lat <= 90):
            raise ValueError(f"lat must be in [-90, 90], got {lat}")
        if not (-180 <= lon <= 180):
            raise ValueError(f"lon must be in [-180, 180], got {lon}")
        if alt_m < -500:
            raise ValueError(f"alt_m is unreasonably low: {alt_m}")
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
        if not (-90 <= lat <= 90):
            raise ValueError(f"lat must be in [-90, 90], got {lat}")
        if not (-180 <= lon <= 180):
            raise ValueError(f"lon must be in [-180, 180], got {lon}")
        if alt_m < -500:
            raise ValueError(f"alt_m is unreasonably low: {alt_m}")
        observer = Topos(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt_m)
        if time_obj is None:
            t = self.ts.now()
        else:
            # Bug fix: ts.from_datetime() requires a timezone-aware datetime.
            # Naive datetimes are assumed UTC and made aware before conversion.
            if time_obj.tzinfo is None:
                time_obj = time_obj.replace(tzinfo=timezone.utc)
            t = self.ts.from_datetime(time_obj)
        difference = self.sat - observer
        topocentric = difference.at(t)
        alt, az, distance = topocentric.altaz()
        return az.degrees, alt.degrees, distance.km
