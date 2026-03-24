import Foundation
import Combine

@MainActor
final class AlertsViewModel: ObservableObject {

    // MARK: – Published

    @Published private(set) var alerts      : [AnomalyAlert] = []
    @Published private(set) var isPolling   : Bool = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var lastUpdated : Date?

    // For tab badge
    @Published private(set) var unreadCount : Int = 0

    // MARK: – Private

    private let api      = APIClient()
    private var serverURL: URL = AppConfig.defaultServerURL
    private var pollTask : Task<Void, Never>?
    private var knownIDs : Set<UUID> = []

    // MARK: – Configuration

    func configure(serverURL: URL) {
        self.serverURL = serverURL
    }

    // MARK: – Polling lifecycle

    func startPolling() {
        guard pollTask == nil else { return }
        isPolling = true
        pollTask  = Task {
            while !Task.isCancelled {
                await fetchAlerts()
                try? await Task.sleep(for: .seconds(AppConfig.alertPollInterval))
            }
        }
    }

    func stopPolling() {
        pollTask?.cancel()
        pollTask  = nil
        isPolling = false
    }

    // MARK: – Manual refresh

    func refresh() {
        Task { await fetchAlerts() }
    }

    func markAllRead() {
        knownIDs   = Set(alerts.map(\.id))
        unreadCount = 0
    }

    // MARK: – Private fetch

    private func fetchAlerts() async {
        do {
            let fetched = try await api.fetchAlerts(base: serverURL)
            errorMessage = nil
            lastUpdated  = .now

            // Detect new alerts for badge
            let newAlerts = fetched.filter { !knownIDs.contains($0.id) }
            unreadCount  += newAlerts.count

            alerts = fetched
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

