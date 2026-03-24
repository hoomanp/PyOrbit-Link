import Foundation
import SwiftUI

// MARK: – Anomaly alert from /api/alerts

struct AnomalyAlert: Identifiable, Decodable {
    let id          = UUID()
    let status      : String    // "WARNING" | "CRITICAL"
    let explanation : String
    let timestamp   : String    // ISO-8601

    enum CodingKeys: String, CodingKey {
        case status, explanation, timestamp
    }

    var severity: Severity {
        status.uppercased() == "CRITICAL" ? .critical : .warning
    }

    var formattedTime: String {
        guard let date = ISO8601DateFormatter().date(from: timestamp) else { return timestamp }
        let f = DateFormatter()
        f.timeStyle = .medium
        f.dateStyle = .none
        return f.string(from: date)
    }

    enum Severity {
        case warning, critical

        var color: Color {
            switch self {
            case .warning:  return .orange
            case .critical: return .red
            }
        }

        var icon: String {
            switch self {
            case .warning:  return "exclamationmark.triangle.fill"
            case .critical: return "xmark.octagon.fill"
            }
        }

        var label: String {
            switch self {
            case .warning:  return "WARNING"
            case .critical: return "CRITICAL"
            }
        }
    }
}

// MARK: – Planner result

struct PlanResult: Decodable {
    let function : String?
    let params   : [String: AnyCodable]?
    let result   : PlanExecResult?
    let error    : String?
}

struct PlanExecResult: Decodable {
    let azimuth    : Double?
    let elevation  : Double?
    let range      : Double?
    let fspl       : Double?
    let events     : [PassEvent]?
    let error      : String?
}

// MARK: – Type-erased JSON value for arbitrary param maps

struct AnyCodable: Decodable, CustomStringConvertible {
    let value: Any

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let v = try? container.decode(Bool.self)   { value = v; return }
        if let v = try? container.decode(Int.self)    { value = v; return }
        if let v = try? container.decode(Double.self) { value = v; return }
        if let v = try? container.decode(String.self) { value = v; return }
        value = ""
    }

    var description: String { "\(value)" }
}
