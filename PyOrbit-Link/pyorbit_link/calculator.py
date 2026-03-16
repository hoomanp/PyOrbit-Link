import numpy as np

class LinkCalculator:
    """Calculates RF Link Budget and Doppler shift for Satellite Communications."""
    
    SPEED_OF_LIGHT = 299792458  # m/s

    @staticmethod
    def calculate_fspl(frequency_hz, distance_km):
        """Free-Space Path Loss (FSPL) in dB."""
        distance_m = distance_km * 1000
        fspl = 20 * np.log10(distance_m) + 20 * np.log10(frequency_hz) + 20 * np.log10(4 * np.pi / LinkCalculator.SPEED_OF_LIGHT)
        return fspl

    @staticmethod
    def calculate_doppler_shift(center_freq_hz, relative_velocity_mps):
        """Doppler shift calculation based on relative velocity between Ground and Sat."""
        doppler_shift = (relative_velocity_mps / LinkCalculator.SPEED_OF_LIGHT) * center_freq_hz
        return doppler_shift

    @staticmethod
    def calculate_antenna_gain(diameter_m, frequency_hz, efficiency=0.55):
        """Calculate antenna gain in dBi based on aperture diameter."""
        wavelength = LinkCalculator.SPEED_OF_LIGHT / frequency_hz
        gain_linear = efficiency * (np.pi * diameter_m / wavelength)**2
        return 10 * np.log10(gain_linear)

    @staticmethod
    def calculate_atmospheric_loss(elevation_deg, frequency_ghz, rain_rate_mm_hr=0):
        """Simple model for atmospheric attenuation based on elevation and rain."""
        # Bug fix: clamp elevation to at least 1 degree to avoid division by zero
        # (sin(0) = 0 causes ZeroDivisionError / inf at horizon).
        elevation_deg = max(elevation_deg, 1.0)
        # Baseline loss increases as elevation drops (more atmosphere to travel through)
        baseline_loss = 0.5 / np.sin(np.radians(elevation_deg))
        
        # Simple rain attenuation model (Rain fade is significant above 10 GHz)
        rain_loss = 0
        if rain_rate_mm_hr > 0 and frequency_ghz > 10:
            rain_loss = 0.5 * (frequency_ghz / 10)**2 * (rain_rate_mm_hr / 10)
            
        return baseline_loss + rain_loss

    @staticmethod
    def total_link_budget(tx_power_dbw, tx_gain_dbi, rx_gain_dbi, path_loss_db, noise_temp_k, bandwidth_hz, atmospheric_loss_db=0):
        """Simple Link Budget calculation (CNR - Carrier to Noise Ratio)."""
        BOLTZMANN_CONSTANT_DB = -228.6  # dB(W/K/Hz)

        rx_power_dbw = tx_power_dbw + tx_gain_dbi + rx_gain_dbi - path_loss_db - atmospheric_loss_db
        noise_power_dbw = BOLTZMANN_CONSTANT_DB + 10 * np.log10(noise_temp_k) + 10 * np.log10(bandwidth_hz)
        # Bug fix: cnr_db was never computed or returned; function always returned None.
        cnr_db = rx_power_dbw - noise_power_dbw
        return cnr_db

    @staticmethod
    def export_results_json(results_dict, filename="link_results.json"):
        """Export calculation results for downstream analysis."""
        import json
        with open(filename, 'w') as f:
            json.dump(results_dict, f, indent=4)
        print(f"Results exported to {filename}")
