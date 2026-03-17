from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class LocationProvider:
    """Utility to convert ZIP codes and addresses to Lat/Lon for satellite tracking."""

    def __init__(self, user_agent="PyOrbitLink"):
        self.geolocator = Nominatim(user_agent=user_agent)
        # Optimization: cache resolved locations to avoid redundant Nominatim API calls
        # and stay within the Nominatim ToS (1 request/second limit).
        self._cache = {}

    def get_lat_lon(self, query):
        """Resolves a query (ZIP, City, Address) to (Latitude, Longitude)."""
        if query in self._cache:
            return self._cache[query]
        try:
            # Explicit timeout prevents the Flask worker from blocking indefinitely.
            location = self.geolocator.geocode(query, timeout=5)
            if location:
                result = location.latitude, location.longitude, location.address
            else:
                result = None, None, None
            self._cache[query] = result
            return result
        except GeocoderTimedOut:
            print("Error: Geocoding service timed out.")
            return None, None, None
        except Exception as e:
            print(f"Error resolving location: {e}")
            return None, None, None
