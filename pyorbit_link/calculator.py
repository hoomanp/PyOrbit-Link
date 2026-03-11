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
    def total_link_budget(tx_power_dbw, tx_gain_dbi, rx_gain_dbi, path_loss_db, noise_temp_k, bandwidth_hz):
        """Simple Link Budget calculation (CNR - Carrier to Noise Ratio)."""
        BOLTZMANN_CONSTANT_DB = -228.6  # dB(W/K/Hz)
        
        rx_power_dbw = tx_power_dbw + tx_gain_dbi + rx_gain_dbi - path_loss_db
        noise_power_dbw = BOLTZMANN_CONSTANT_DB + 10 * np.log10(noise_temp_k) + 10 * np.log10(bandwidth_hz)
        
        cnr_db = rx_power_dbw - noise_power_dbw
        return rx_power_dbw, cnr_db
