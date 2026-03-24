import Foundation
import CoreLocation

// MARK: – Raw API telemetry payload

struct TelemetryPayload: Decodable {
    let azimuth:   Double   // degrees 0-360
    let elevation: Double   // degrees above horizon
    let range:     Double   // km
    let fspl:      Double   // free-space path loss in dB
    let latitude:  Double   // observer latitude
    let longitude: Double   // observer longitude
}

// MARK: – Time-stamped snapshot (stored in rolling history)

struct TelemetrySnapshot: Identifiable {
    let id        = UUID()
    let timestamp : Date
    let azimuth   : Double
    let elevation : Double
    let range     : Double
    let fspl      : Double
    let observerCoordinate: CLLocationCoordinate2D

    var isVisible: Bool { elevation > 5 }

    /// Rough satellite coordinate from observer + AER (approximation for map display)
    var approximateSatelliteCoordinate: CLLocationCoordinate2D {
        let earthRadius = 6371.0   // km
        let distGround  = range * cos(elevation * .pi / 180)
        let latRad      = observerCoordinate.latitude  * .pi / 180
        let lonRad      = observerCoordinate.longitude * .pi / 180
        let azRad       = azimuth * .pi / 180
        let angDist     = distGround / earthRadius
        let newLat      = asin(sin(latRad) * cos(angDist) +
                               cos(latRad) * sin(angDist) * cos(azRad))
        let newLon      = lonRad + atan2(sin(azRad) * sin(angDist) * cos(latRad),
                                         cos(angDist) - sin(latRad) * sin(newLat))
        return CLLocationCoordinate2D(latitude:  newLat * 180 / .pi,
                                      longitude: newLon * 180 / .pi)
    }

    /// Signal quality 0–1 derived from elevation (higher = better)
    var elevationQuality: Double {
        min(max(elevation / 90.0, 0), 1)
    }

    /// Link quality 0–1 derived from FSPL (lower FSPL = better link)
    var linkQuality: Double {
        // Typical FSPL range for LEO: 130–165 dB
        let clamped = min(max(fspl, 130), 165)
        return 1.0 - (clamped - 130) / 35.0
    }
}

// MARK: – SSE event types from /api/track/stream

struct SSETelemetryEvent {
    enum Kind {
        case telemetry(TelemetryPayload)
        case token(String)
        case done
        case error(String)
    }
    let kind: Kind
}

// MARK: – Satellite pass event

struct PassEvent: Identifiable, Decodable {
    let id   = UUID()
    let rise : String
    let culmination: String
    let set  : String

    enum CodingKeys: String, CodingKey {
        case rise = "Rise"
        case culmination = "Culmination"
        case set = "Set"
    }

    var riseDate: Date? { ISO8601DateFormatter().date(from: rise) }
    var setDate:  Date? { ISO8601DateFormatter().date(from: set)  }
}

// MARK: – Polar-plot point for sky view

struct PolarPoint: Identifiable {
    let id        = UUID()
    let azimuth   : Double  // degrees
    let elevation : Double  // degrees
    let timestamp : Date
}
