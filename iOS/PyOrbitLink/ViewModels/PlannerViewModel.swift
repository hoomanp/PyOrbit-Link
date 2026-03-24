import Foundation
import Combine

@MainActor
final class PlannerViewModel: ObservableObject {

    // MARK: – Published

    @Published private(set) var result       : PlanResult?
    @Published private(set) var isProcessing : Bool = false
    @Published private(set) var errorMessage : String?
    @Published var inputText: String = ""

    // MARK: – Private

    private let api      = APIClient()
    private var serverURL: URL    = AppConfig.defaultServerURL
    private var noradID  : String = AppConfig.defaultNoradID
    private weak var locationService: LocationService?

    // MARK: – Configuration

    func configure(serverURL: URL, noradID: String, locationService: LocationService) {
        self.serverURL       = serverURL
        self.noradID         = noradID
        self.locationService = locationService
    }

    // MARK: – Plan

    func plan() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isProcessing else { return }

        isProcessing = true
        errorMessage = nil
        result       = nil

        do {
            result = try await api.plan(message: text, base: serverURL)
        } catch {
            errorMessage = error.localizedDescription
        }

        isProcessing = false
    }

    // MARK: – Example prompts

    var examplePrompts: [String] {
        [
            "Track satellite ISS",
            "Find upcoming pass events for the next 2 days",
            "Calculate free-space path loss at 437 MHz"
        ]
    }

    // MARK: – Formatted result display

    var functionCallText: String {
        guard let r = result, let fn = r.function else { return "No function matched" }
        var params = ""
        if let p = r.params {
            params = p.map { "\($0.key): \($0.value)" }.joined(separator: ", ")
        }
        return "\(fn)(\(params))"
    }
}

