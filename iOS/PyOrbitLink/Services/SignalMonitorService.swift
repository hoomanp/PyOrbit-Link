import Foundation
import CoreTelephony
import Network
import Combine

// MARK: – Combines CoreTelephony + NWPathMonitor for real device signal data

@MainActor
final class SignalMonitorService: ObservableObject {

    // MARK: Published
    @Published private(set) var radioTechnology : RadioTechnology = .unknown
    @Published private(set) var carrierName     : String?
    @Published private(set) var isOnWiFi        : Bool  = false
    @Published private(set) var isConnected     : Bool  = false
    @Published private(set) var interfaceType   : String = "Unknown"

    // MARK: Private
    private let networkInfo   = CTTelephonyNetworkInfo()
    private let pathMonitor   = NWPathMonitor()
    private let monitorQueue  = DispatchQueue(label: "com.pyorbitlink.network", qos: .utility)
    private var isStarted     = false

    // MARK: – Lifecycle

    func start() {
        guard !isStarted else { return }
        isStarted = true

        // 1. CoreTelephony — radio technology
        refreshCellularInfo()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(cellularInfoChanged),
            name: NSNotification.Name.CTServiceRadioAccessTechnologyDidChange,
            object: nil
        )

        // 2. NWPathMonitor — path type and connectivity
        pathMonitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.isConnected = path.status == .satisfied
                self.isOnWiFi    = path.usesInterfaceType(.wifi)
                self.interfaceType = self.describeInterface(path)
                // If Wi-Fi path, override radio tech display
                if self.isOnWiFi {
                    self.radioTechnology = .wifi
                }
            }
        }
        pathMonitor.start(queue: monitorQueue)
    }

    func stop() {
        pathMonitor.cancel()
        NotificationCenter.default.removeObserver(self)
        isStarted = false
    }

    // MARK: – Snapshot for a SignalReading

    func snapshot(fspl: Double?, elevation: Double?, gpsAccuracy: Double?) -> SignalReading {
        SignalReading(
            timestamp   : .now,
            radioTech   : radioTechnology,
            carrierName : carrierName,
            gpsAccuracy : gpsAccuracy,
            gpsHDOP     : nil,   // not provided by CLLocation directly
            isOnWiFi    : isOnWiFi,
            fspl        : fspl,
            elevation   : elevation
        )
    }

    // MARK: – Private helpers

    @objc private nonisolated func cellularInfoChanged() {
        Task { @MainActor in refreshCellularInfo() }
    }

    private func refreshCellularInfo() {
        // CTTelephonyNetworkInfo returns a dict keyed by service ID in iOS 12+
        if let techs = networkInfo.serviceCurrentRadioAccessTechnology {
            // Pick first valid entry
            let tech = techs.values.first
            radioTechnology = RadioTechnology(cttechString: tech)
        }

        if let carriers = networkInfo.serviceSubscriberCellularProviders {
            carrierName = carriers.values.compactMap(\.carrierName).first
        }
    }

    private func describeInterface(_ path: NWPath) -> String {
        if path.usesInterfaceType(.wifi)     { return "Wi-Fi" }
        if path.usesInterfaceType(.cellular) { return "Cellular" }
        if path.usesInterfaceType(.wiredEthernet) { return "Ethernet" }
        if path.usesInterfaceType(.loopback) { return "Loopback" }
        return "Other"
    }
}
