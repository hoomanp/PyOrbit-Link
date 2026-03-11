import requests

class CelesTrakAPI:
    """Fetcher for the latest Two-Line Elements (TLEs) from CelesTrak."""
    BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"

    @staticmethod
    def get_tle_by_norad_id(norad_id):
        """Fetch TLE for a specific NORAD ID (e.g., 25544 for ISS)."""
        params = {'CATNR': norad_id, 'FORMAT': 'TLE'}
        try:
            response = requests.get(CelesTrakAPI.BASE_URL, params=params)
            response.raise_for_status()
            lines = response.text.strip().splitlines()
            if len(lines) >= 3:
                return lines[0].strip(), lines[1].strip(), lines[2].strip()
            return None
        except Exception as e:
            print(f"Error fetching TLE: {e}")
            return None
