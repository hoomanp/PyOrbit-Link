import logging
import requests

logger = logging.getLogger(__name__)

class CelesTrakAPI:
    """Fetcher for the latest Two-Line Elements (TLEs) from CelesTrak."""
    BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"

    @staticmethod
    def _validate_tle(name, line1, line2):
        """Validate TLE field lengths, line identifiers, and checksums."""
        if not (1 <= len(name) <= 24):
            return False
        if len(line1) != 69 or not line1.startswith('1 '):
            return False
        if len(line2) != 69 or not line2.startswith('2 '):
            return False
        for line in (line1, line2):
            checksum = sum(
                int(c) if c.isdigit() else (1 if c == '-' else 0)
                for c in line[:-1]
            ) % 10
            if checksum != int(line[-1]):
                return False
        return True

    @staticmethod
    def get_tle_by_norad_id(norad_id):
        """Fetch TLE for a specific NORAD ID (e.g., 25544 for ISS)."""
        params = {'CATNR': norad_id, 'FORMAT': 'TLE'}
        try:
            response = requests.get(CelesTrakAPI.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            lines = response.text.strip().splitlines()
            if len(lines) >= 3:
                name, line1, line2 = lines[0].strip(), lines[1].strip(), lines[2].strip()
                # Security: validate TLE format and checksums before trusting the data.
                if not CelesTrakAPI._validate_tle(name, line1, line2):
                    logger.error("TLE validation failed for NORAD ID %s — data may be malformed or tampered", norad_id)
                    return None
                return name, line1, line2
            return None
        except Exception:
            logger.exception("Error fetching TLE for NORAD ID %s", norad_id)
            return None
