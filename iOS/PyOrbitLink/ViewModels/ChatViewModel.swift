import Foundation
import Combine

@MainActor
final class ChatViewModel: ObservableObject {

    // MARK: – Published

    @Published private(set) var messages    : [ChatMessage] = []
    @Published private(set) var isWaiting   : Bool = false
    @Published private(set) var turnCount   : Int  = 0
    @Published private(set) var errorMessage: String?
    @Published var inputText: String = ""

    // MARK: – Private

    private let api      = APIClient()
    private var serverURL: URL   = AppConfig.defaultServerURL
    private var noradID  : String = AppConfig.defaultNoradID

    var isAtLimit: Bool { turnCount >= AppConfig.maxChatTurns }

    // MARK: – Configuration

    func configure(serverURL: URL, noradID: String) {
        self.serverURL = serverURL
        self.noradID   = noradID
    }

    // MARK: – Send

    func send() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isWaiting, !isAtLimit else { return }

        inputText    = ""
        errorMessage = nil

        let userMsg = ChatMessage(role: .user, content: text)
        messages.append(userMsg)

        // Placeholder for streaming response
        let assistantMsg = ChatMessage(role: .assistant, content: "", isStreaming: true)
        messages.append(assistantMsg)
        isWaiting = true

        do {
            let response = try await api.chat(message: text, base: serverURL)
            // Update the placeholder in-place
            if let idx = messages.firstIndex(where: { $0.id == assistantMsg.id }) {
                messages[idx] = ChatMessage(role: .assistant,
                                            content: response.reply,
                                            isStreaming: false)
            }
            turnCount = response.turns
        } catch {
            if let idx = messages.firstIndex(where: { $0.id == assistantMsg.id }) {
                messages.remove(at: idx)
            }
            errorMessage = error.localizedDescription
        }

        isWaiting = false
    }

    // MARK: – Reset

    func resetSession() async {
        do {
            _ = try await api.resetChat(base: serverURL)
            messages.removeAll()
            turnCount    = 0
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    // MARK: – Quick prompts

    var quickPrompts: [String] {
        [
            "What is the current satellite pass quality?",
            "Analyse signal health and FSPL.",
            "Predict next optimal pass window.",
            "Explain free-space path loss for this orbit."
        ]
    }
}

