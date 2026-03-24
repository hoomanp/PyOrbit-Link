import Foundation
import SwiftUI

// MARK: – One reading collected by SignalMonitorService

struct SignalReading: Identifiable {
    let id          = UUID()
    let timestamp   : Date
    let radioTech   : RadioTechnology    // from CoreTelephony
    let carrierName : String?
    let gpsAccuracy : Double?            // metres (from CoreLocation)
    let gpsHDOP     : Double?            // horizontal dilution of precision
    let isOnWiFi    : Bool               // from NWPathMonitor
    let fspl        : Double?            // latest FSPL from backend (dB)
    let elevation   : Double?           // latest satellite elevation (°)

    // MARK: Derived signal quality

    /// Link-budget quality 0–1: uses FSPL when available, falls back to elevation
    var linkQuality: Double {
        if let f = fspl {
            let clamped = min(max(f, 130), 165)
            return 1.0 - (clamped - 130) / 35.0
        }
        if let e = elevation {
            return min(max(e / 90.0, 0), 1)
        }
        return 0
    }

    var linkQualityLabel: String {
        switch linkQuality {
        case 0.8...: return "Excellent"
        case 0.6..<0.8: return "Good"
        case 0.4..<0.6: return "Fair"
        case 0.2..<0.4: return "Poor"
        default:        return "No Link"
        }
    }

    var linkQualityColor: Color {
        switch linkQuality {
        case 0.8...: return .green
        case 0.6..<0.8: return .mint
        case 0.4..<0.6: return .yellow
        case 0.2..<0.4: return .orange
        default:        return .red
        }
    }
}

// MARK: – Radio technology from CTTelephonyNetworkInfo

enum RadioTechnology: String, CaseIterable {
    case nr      = "5G NR"
    case nrNSA   = "5G NSA"
    case lte     = "LTE"
    case wcdma   = "WCDMA"
    case gsm     = "GSM"
    case wifi    = "Wi-Fi"
    case unknown = "Unknown"

    init(cttechString: String?) {
        guard let s = cttechString else { self = .unknown; return }
        switch s {
        case "CTRadioAccessTechnologyNRSA":             self = .nr
        case "CTRadioAccessTechnologyNR":               self = .nrNSA
        case "CTRadioAccessTechnologyLTE":              self = .lte
        case "CTRadioAccessTechnologyWCDMA",
             "CTRadioAccessTechnologyHSDPA",
             "CTRadioAccessTechnologyHSUPA",
             "CTRadioAccessTechnologyCDMAEVDORev0",
             "CTRadioAccessTechnologyCDMAEVDORevA",
             "CTRadioAccessTechnologyCDMAEVDORevB":     self = .wcdma
        case "CTRadioAccessTechnologyEdge",
             "CTRadioAccessTechnologyGPRS",
             "CTRadioAccessTechnologyCDMA1x":           self = .gsm
        default:                                        self = .unknown
        }
    }

    var icon: String {
        switch self {
        case .nr, .nrNSA: return "5.circle.fill"
        case .lte:         return "4.circle.fill"
        case .wcdma:       return "3.circle.fill"
        case .gsm:         return "2.circle.fill"
        case .wifi:        return "wifi"
        case .unknown:     return "antenna.radiowaves.left.and.right.slash"
        }
    }

    var color: Color {
        switch self {
        case .nr, .nrNSA: return .cyan
        case .lte:         return .blue
        case .wcdma:       return .indigo
        case .gsm:         return .purple
        case .wifi:        return .green
        case .unknown:     return .gray
        }
    }
}

// MARK: – GPS accuracy category

enum GPSAccuracy {
    case high, medium, low, unavailable

    init(_ metres: Double?) {
        switch metres {
        case .none:        self = .unavailable
        case ..<10:        self = .high
        case 10..<30:      self = .medium
        default:           self = .low
        }
    }

    var label: String {
        switch self {
        case .high:        return "High (<10 m)"
        case .medium:      return "Medium (10–30 m)"
        case .low:         return "Low (>30 m)"
        case .unavailable: return "Unavailable"
        }
    }

    var color: Color {
        switch self {
        case .high:        return .green
        case .medium:      return .yellow
        case .low:         return .orange
        case .unavailable: return .red
        }
    }
}
