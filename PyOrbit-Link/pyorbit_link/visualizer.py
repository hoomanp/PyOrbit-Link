import matplotlib.pyplot as plt
import numpy as np

class SatVisualizer:
    """Visualize satellite paths across the sky."""
    
    @staticmethod
    def plot_polar_pass(azimuths_deg, elevations_deg, title="Satellite Pass"):
        """Plot a satellite pass on a polar chart (Radar style)."""
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, polar=True)
        
        # In polar plots, 0 degrees is usually East. 
        # We need to rotate so 0 is North and go clockwise.
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        
        # Convert to radians for matplotlib
        az_rad = np.radians(azimuths_deg)
        # 90 deg elevation = center (radius 0)
        # 0 deg elevation = outer edge (radius 90)
        r = 90 - np.array(elevations_deg)
        
        ax.plot(az_rad, r, marker='o', linestyle='-', color='b', markersize=4)
        ax.set_rmax(90)
        ax.set_rticks([0, 30, 60, 90])
        ax.set_yticklabels(['90°', '60°', '30°', '0°']) # Elevation labels
        ax.set_title(title, va='bottom')
        
        plt.show()
