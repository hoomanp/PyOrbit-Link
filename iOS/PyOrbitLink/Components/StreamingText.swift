import SwiftUI

// MARK: – Text view with typewriter cursor when streaming

struct StreamingText: View {

    let text: String
    let isStreaming: Bool
    var font: Font = .body
    var color: Color = .primary

    @State private var showCursor: Bool = true
    private let cursorTimer = Timer.publish(every: 0.5, on: .main, in: .common).autoconnect()

    var body: some View {
        Group {
            if text.isEmpty && isStreaming {
                placeholder
            } else {
                textWithCursor
            }
        }
    }

    private var textWithCursor: some View {
        (Text(text).font(font).foregroundStyle(color) +
         (isStreaming ? Text(showCursor ? "▌" : " ").font(font).foregroundStyle(color.opacity(0.7)) : Text("")))
        .onReceive(cursorTimer) { _ in
            if isStreaming { showCursor.toggle() }
        }
    }

    private var placeholder: some View {
        HStack(spacing: 4) {
            Text("Analysing")
                .font(font)
                .foregroundStyle(.secondary)
            ThinkingDots()
        }
    }
}

// MARK: – Animated thinking dots

struct ThinkingDots: View {

    @State private var phase: Int = 0

    var body: some View {
        HStack(spacing: 3) {
            ForEach(0..<3, id: \.self) { i in
                Circle()
                    .fill(Color.secondary.opacity(phase == i ? 1 : 0.3))
                    .frame(width: 5, height: 5)
                    .scaleEffect(phase == i ? 1.2 : 0.8)
                    .animation(.easeInOut(duration: 0.3).delay(Double(i) * 0.15), value: phase)
            }
        }
        .onAppear {
            Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
                phase = (phase + 1) % 3
            }
        }
    }
}

// MARK: – Chat bubble

struct ChatBubble: View {

    let message: ChatMessage

    var body: some View {
        HStack {
            if message.isUser { Spacer(minLength: 60) }

            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 4) {
                if message.isStreaming {
                    StreamingText(text: message.content,
                                  isStreaming: true,
                                  font: .callout)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(message.bubbleColor, in: bubbleShape(isUser: message.isUser))
                } else {
                    Text(message.content)
                        .font(.callout)
                        .foregroundStyle(message.textColor)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(message.bubbleColor, in: bubbleShape(isUser: message.isUser))
                        .textSelection(.enabled)
                }

                Text(message.timestamp, style: .time)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }

            if !message.isUser { Spacer(minLength: 60) }
        }
    }

    private func bubbleShape(isUser: Bool) -> some Shape {
        UnevenRoundedRectangle(
            topLeadingRadius:     isUser ? 18 : 4,
            bottomLeadingRadius:  18,
            bottomTrailingRadius: isUser ? 4  : 18,
            topTrailingRadius:    18
        )
    }
}
