from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class LocationProvider:
    """Utility to convert ZIP codes and addresses to Lat/Lon for satellite tracking."""
    
    def __init__(self, user_agent="PyOrbitLink"):
        self.geolocator = Nominatim(user_agent=user_agent)

    def get_lat_lon(self, query):
        """Resolves a query (ZIP, City, Address) to (Latitude, Longitude)."""
        try:
            location = self.geolocator.geocode(query)
            if location:
                return location.latitude, location.longitude, location.address
            return None, None, None
        except GeocoderTimedOut:
            print("Error: Geocoding service timed out.")
            return None, None, None
        except Exception as e:
            print(f"Error resolving location: {e}")
            return None, None, None
