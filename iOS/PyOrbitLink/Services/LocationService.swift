import Foundation
import CoreLocation
import Combine

// MARK: – CoreLocation wrapper publishing real device GPS

@MainActor
final class LocationService: NSObject, ObservableObject, CLLocationManagerDelegate {

    // MARK: Published state
    @Published private(set) var coordinate  : CLLocationCoordinate2D? = DemoLocation.coordinate
    @Published private(set) var accuracy    : Double?           // metres
    @Published private(set) var altitude    : Double?           // metres
    @Published private(set) var heading     : Double?           // degrees magnetic
    @Published private(set) var authStatus  : CLAuthorizationStatus = .notDetermined
    @Published private(set) var isAvailable : Bool = false
    @Published private(set) var lastError   : Error?

    private let manager: CLLocationManager

    override init() {
        manager = CLLocationManager()
        super.init()
        manager.delegate           = self
        manager.desiredAccuracy    = kCLLocationAccuracyBest
        manager.distanceFilter     = 1      // update every 1 metre
        manager.headingFilter      = 5      // update every 5°
    }

    // MARK: – Permission

    func requestPermission() async {
        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse, .authorizedAlways:
            startUpdating()
        default:
            break
        }
    }

    // MARK: – Start / stop

    func startUpdating() {
        manager.startUpdatingLocation()
        manager.startUpdatingHeading()
    }

    func stopUpdating() {
        manager.stopUpdatingLocation()
        manager.stopUpdatingHeading()
    }

    // MARK: – Convenience: current lat/lon as strings for API

    var latString: String {
        guard let c = coordinate else { return DemoLocation.latString }
        return String(format: "%.6f", c.latitude)
    }
    var lonString: String {
        guard let c = coordinate else { return DemoLocation.lonString }
        return String(format: "%.6f", c.longitude)
    }

    // MARK: – CLLocationManagerDelegate

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        Task { @MainActor in
            self.coordinate  = loc.coordinate
            self.accuracy    = loc.horizontalAccuracy > 0 ? loc.horizontalAccuracy : nil
            self.altitude    = loc.altitude
            self.isAvailable = true
            self.lastError   = nil
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didUpdateHeading newHeading: CLHeading) {
        Task { @MainActor in
            self.heading = newHeading.magneticHeading
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didFailWithError error: Error) {
        Task { @MainActor in
            self.lastError   = error
            self.isAvailable = false
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        Task { @MainActor in
            self.authStatus = manager.authorizationStatus
            switch manager.authorizationStatus {
            case .authorizedWhenInUse, .authorizedAlways:
                self.startUpdating()
            default:
                break
            }
        }
    }
}
