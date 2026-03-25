import Foundation
import CoreLocation
import Combine

@MainActor
final class LiveTrackViewModel: ObservableObject {

    // MARK: – Published state

    @Published private(set) var latestSnapshot : TelemetrySnapshot?
    @Published private(set) var aerHistory     : [TelemetrySnapshot] = []
    @Published private(set) var polarHistory   : [PolarPoint]        = []
    @Published private(set) var aiText         : String              = ""
    @Published private(set) var streamState    : StreamState         = .idle
    @Published private(set) var passEvents     : [PassEvent]         = []
    @Published private(set) var errorMessage   : String?

    enum StreamState { case idle, connecting, streaming, done, error }

    // MARK: – Private

    private let api     = APIClient()
    private let sse     = SSEStreamClient()
    private var streamTask: Task<Void, Never>?
    private var serverURL : URL = AppConfig.defaultServerURL
    private var noradID   : String = AppConfig.defaultNoradID
    private weak var locationService: LocationService?

    private var historyLimit: Int { AppConfig.aerHistorySeconds }

    // MARK: – Configuration

    func configure(serverURL: URL, noradID: String, locationService: LocationService) {
        self.serverURL       = serverURL
        self.noradID         = noradID
        self.locationService = locationService
        loadDemoHistory()
    }

    /// Pre-populate charts and telemetry cards with the Tarzana, CA sample pass
    /// so the UI shows realistic data immediately on launch.
    private func loadDemoHistory() {
        let history = SamplePass.buildHistory()
        aerHistory     = history
        polarHistory   = history.map { PolarPoint(azimuth: $0.azimuth,
                                                  elevation: $0.elevation,
                                                  timestamp: $0.timestamp) }
        latestSnapshot = SamplePass.latestSnapshot()
        aiText         = SamplePass.demoAIText
    }

    // MARK: – Stream control

    func startStream() {
        guard streamState != .streaming, streamState != .connecting else { return }
        streamTask?.cancel()
        aiText      = ""
        streamState = .connecting
        errorMessage = nil

        streamTask = Task {
            let lat = locationService?.latString ?? "0"
            let lon = locationService?.lonString ?? "0"
            let query: [String: String] = [
                "lat"   : lat,
                "lon"   : lon,
                "norad" : noradID
            ]
            do {
                let stream = await sse.stream(path: "/api/track/stream", query: query,
                                              base: serverURL)
                streamState = .streaming
                for try await event in stream {
                    if Task.isCancelled { break }
                    handle(event: event)
                }
                if streamState == .streaming { streamState = .done }
            } catch {
                streamState  = .error
                errorMessage = error.localizedDescription
            }
        }
    }

    func stopStream() {
        streamTask?.cancel()
        streamTask  = nil
        streamState = .idle
    }

    func refreshPassEvents() {
        Task {
            do {
                let lat = locationService?.latString ?? "0"
                let lon = locationService?.lonString ?? "0"
                passEvents = try await api.getWithQuery(
                    "/api/pass_events",
                    query: ["lat": lat, "lon": lon, "norad": noradID, "days": "3"],
                    base: serverURL
                )
            } catch {
                // pass events are optional – don't surface errors
            }
        }
    }

    // MARK: – Event handler

    private func handle(event: SSETelemetryEvent) {
        switch event.kind {
        case .telemetry(let payload):
            let coord = locationService?.coordinate ??
                        CLLocationCoordinate2D(latitude: Double(locationService?.latString ?? "0") ?? 0,
                                               longitude: Double(locationService?.lonString ?? "0") ?? 0)
            let snap = TelemetrySnapshot(
                timestamp          : .now,
                azimuth            : payload.azimuth,
                elevation          : payload.elevation,
                range              : payload.range,
                fspl               : payload.fspl,
                observerCoordinate : coord,
                satelliteName      : payload.satName
            )
            latestSnapshot = snap
            appendToHistory(snap)

        case .token(let text):
            aiText += text

        case .done:
            streamState = .done

        case .error(let msg):
            streamState  = .error
            errorMessage = msg
        }
    }

    private func appendToHistory(_ snap: TelemetrySnapshot) {
        aerHistory.append(snap)
        if aerHistory.count > historyLimit { aerHistory.removeFirst() }

        polarHistory.append(PolarPoint(azimuth:   snap.azimuth,
                                       elevation: snap.elevation,
                                       timestamp: snap.timestamp))
        if polarHistory.count > historyLimit { polarHistory.removeFirst() }
    }
}

