import Foundation
import Combine

@MainActor
final class SignalViewModel: ObservableObject {

    // MARK: – Published

    @Published private(set) var readings        : [SignalReading] = []
    @Published private(set) var latestReading   : SignalReading?
    @Published private(set) var isCollecting    : Bool = false
    @Published private(set) var gpsAccuracyText : String = "—"

    // MARK: – Private

    private var timer        : Timer?
    private var serverURL    : URL = AppConfig.defaultServerURL
    private var noradID      : String = AppConfig.defaultNoradID
    private weak var locationService: LocationService?
    private weak var signalService  : SignalMonitorService?

    // Latest telemetry from the live-track stream (injected externally)
    var latestFSPL      : Double?
    var latestElevation : Double?

    private let maxReadings = AppConfig.signalHistorySeconds

    // MARK: – Configuration

    func configure(locationService: LocationService,
                   signalService:   SignalMonitorService,
                   serverURL: URL,
                   noradID:   String) {
        self.locationService = locationService
        self.signalService   = signalService
        self.serverURL       = serverURL
        self.noradID         = noradID
    }

    // MARK: – Collection control

    func startCollecting() {
        guard !isCollecting else { return }
        isCollecting = true
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in self?.collect() }
        }
        collect()   // immediate first reading
    }

    func stopCollecting() {
        timer?.invalidate()
        timer        = nil
        isCollecting = false
    }

    // MARK: – Data

    var linkQualityHistory: [(time: Date, quality: Double)] {
        readings.map { ($0.timestamp, $0.linkQuality) }
    }

    var fsplHistory: [(time: Date, fspl: Double)] {
        readings.compactMap {
            guard let f = $0.fspl else { return nil }
            return ($0.timestamp, f)
        }
    }

    var elevationHistory: [(time: Date, elevation: Double)] {
        readings.compactMap {
            guard let e = $0.elevation else { return nil }
            return ($0.timestamp, e)
        }
    }

    var gpsAccuracyHistory: [(time: Date, accuracy: Double)] {
        readings.compactMap {
            guard let a = $0.gpsAccuracy else { return nil }
            return ($0.timestamp, a)
        }
    }

    // MARK: – Private

    private func collect() {
        guard let sig = signalService, let loc = locationService else { return }

        let reading = sig.snapshot(
            fspl:        latestFSPL,
            elevation:   latestElevation,
            gpsAccuracy: loc.accuracy
        )
        latestReading = reading

        if let acc = loc.accuracy {
            gpsAccuracyText = String(format: "±%.0f m", acc)
        } else {
            gpsAccuracyText = "—"
        }

        readings.append(reading)
        if readings.count > maxReadings { readings.removeFirst() }
    }
}

private extension AppConfig {
    static let defaultServerURL = URL(string: "http://\(AppConfig.defaultHost):\(AppConfig.defaultPort)")!
    static let defaultNoradID   = "25544"
}
