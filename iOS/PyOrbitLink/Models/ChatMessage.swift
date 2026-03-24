import Foundation
import SwiftUI

// MARK: – Chat message

struct ChatMessage: Identifiable, Equatable {
    let id        = UUID()
    let role      : Role
    var content   : String
    var isStreaming: Bool = false
    let timestamp : Date  = .now

    enum Role: String {
        case user, assistant, system
    }

    var isUser: Bool { role == .user }

    var bubbleColor: Color {
        role == .user ? Color.accentColor : Color(uiColor: .secondarySystemBackground)
    }

    var textColor: Color {
        role == .user ? .white : .primary
    }

    var alignment: HorizontalAlignment {
        role == .user ? .trailing : .leading
    }

    var frameAlignment: Alignment {
        role == .user ? .trailing : .leading
    }
}

// MARK: – Chat API types

struct ChatRequest: Encodable {
    let message: String
}

struct ChatResponse: Decodable {
    let reply  : String
    let turns  : Int
}

struct ChatResetResponse: Decodable {
    let status: String
}
