import Foundation
import CoreLocation

// MARK: – Demo location (ZIP 91356-4144, Tarzana, CA)

enum DemoLocation {
    static let latitude:  Double = 34.1675
    static let longitude: Double = -118.5504
    static let coordinate = CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    static let label      = "Tarzana, CA 91356"

    static var latString: String { String(format: "%.6f", latitude)  }
    static var lonString: String { String(format: "%.6f", longitude) }
}

// MARK: – Pre-computed ISS pass arc over Tarzana, CA
// A realistic 15-point arc: rising SW → peaking high W → setting NW
// Computed for 437.525 MHz (UHF amateur) using free-space path loss model.

enum SamplePass {

    struct Frame {
        let secondsAgo: TimeInterval   // negative = past
        let azimuth:    Double         // degrees
        let elevation:  Double         // degrees
        let range:      Double         // km
        let fspl:       Double         // dB  FSPL = 20·log10(4π·d·f/c)
    }

    // FSPL factor at 437.525 MHz: 20·log10(4π·437525000/299792458) + 60 ≈ 85.27
    static let arc: [Frame] = [
        Frame(secondsAgo: -420, azimuth: 220.1, elevation:  5.2, range: 1420.0, fspl: 148.3),
        Frame(secondsAgo: -390, azimuth: 224.4, elevation:  9.1, range: 1148.0, fspl: 146.5),
        Frame(secondsAgo: -360, azimuth: 230.2, elevation: 14.3, range: 952.0,  fspl: 144.8),
        Frame(secondsAgo: -330, azimuth: 238.0, elevation: 20.8, range: 791.0,  fspl: 143.2),
        Frame(secondsAgo: -300, azimuth: 247.5, elevation: 29.7, range: 663.0,  fspl: 141.7),
        Frame(secondsAgo: -270, azimuth: 260.1, elevation: 41.6, range: 571.0,  fspl: 140.4),
        Frame(secondsAgo: -240, azimuth: 280.3, elevation: 55.9, range: 491.0,  fspl: 139.1),
        Frame(secondsAgo: -210, azimuth: 305.8, elevation: 63.2, range: 469.0,  fspl: 138.7),
        Frame(secondsAgo: -180, azimuth: 325.4, elevation: 53.8, range: 506.0,  fspl: 139.3),
        Frame(secondsAgo: -150, azimuth: 336.1, elevation: 41.2, range: 581.0,  fspl: 140.5),
        Frame(secondsAgo: -120, azimuth: 341.9, elevation: 28.5, range: 681.0,  fspl: 141.9),
        Frame(secondsAgo:  -90, azimuth: 345.7, elevation: 19.6, range: 820.0,  fspl: 143.5),
        Frame(secondsAgo:  -60, azimuth: 348.2, elevation: 12.8, range: 1012.0, fspl: 145.4),
        Frame(secondsAgo:  -30, azimuth: 350.0, elevation:  8.1, range: 1241.0, fspl: 147.1),
        Frame(secondsAgo:    0, azimuth: 351.3, elevation:  5.4, range: 1452.0, fspl: 148.5),
    ]

    // Builds TelemetrySnapshot history from the arc
    static func buildHistory() -> [TelemetrySnapshot] {
        let now = Date()
        return arc.map { f in
            TelemetrySnapshot(
                timestamp:          now.addingTimeInterval(f.secondsAgo),
                azimuth:            f.azimuth,
                elevation:          f.elevation,
                range:              f.range,
                fspl:               f.fspl,
                observerCoordinate: DemoLocation.coordinate,
                satelliteName:      "ISS (ZARYA)"
            )
        }
    }

    // Latest frame (most recent in the arc)
    static func latestSnapshot() -> TelemetrySnapshot {
        let f = arc.last!
        return TelemetrySnapshot(
            timestamp:          Date(),
            azimuth:            f.azimuth,
            elevation:          f.elevation,
            range:              f.range,
            fspl:               f.fspl,
            observerCoordinate: DemoLocation.coordinate,
            satelliteName:      "ISS (ZARYA)"
        )
    }

    static let demoAIText = """
    ISS pass over Tarzana, CA analyzed at 437.525 MHz (UHF).

    Peak elevation reached 63.2° — excellent geometry for link margin. \
    Free-space path loss at peak was 138.7 dB (range 469 km), \
    well within budget for a 5 W handheld radio with a 9 dBi Yagi. \
    The pass tracked SW→W→NW over 14 min — a long-duration overhead pass.

    Recommendation: acquire lock at elevation ≥ 8° (FSPL < 148 dB). \
    Doppler shift peaks at ±3.5 kHz around culmination — \
    configure radio for automatic Doppler correction.
    """
}
