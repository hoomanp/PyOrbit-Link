import SwiftUI

struct ChatView: View {

    @ObservedObject var vm: ChatViewModel
    @FocusState private var inputFocused: Bool
    @State private var scrollID: UUID?

    var body: some View {
        VStack(spacing: 0) {
            turnBanner
            messageList
            inputBar
        }
        .background(Color(uiColor: .systemGroupedBackground))
    }

    // MARK: – Turn banner

    private var turnBanner: some View {
        HStack {
            ProgressView(value: Double(vm.turnCount), total: Double(AppConfig.maxChatTurns))
                .tint(turnColor)
                .frame(maxWidth: .infinity)
            Text("\(vm.turnCount)/\(AppConfig.maxChatTurns) turns")
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
                .frame(width: 80, alignment: .trailing)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Color(uiColor: .secondarySystemGroupedBackground))
    }

    // MARK: – Message list

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    if vm.messages.isEmpty {
                        emptyState
                    }
                    ForEach(vm.messages) { msg in
                        ChatBubble(message: msg)
                            .id(msg.id)
                            .transition(.move(edge: msg.isUser ? .trailing : .leading).combined(with: .opacity))
                    }
                    Color.clear.frame(height: 8).id("bottom")
                }
                .padding()
                .animation(.easeInOut(duration: 0.25), value: vm.messages.count)
            }
            .onChange(of: vm.messages.last?.content) { _ in
                withAnimation { proxy.scrollTo("bottom") }
            }
            .onChange(of: vm.messages.count) { _ in
                withAnimation { proxy.scrollTo("bottom") }
            }
        }
    }

    // MARK: – Empty state

    private var emptyState: some View {
        VStack(spacing: 20) {
            Image(systemName: "message.badge.waveform.fill")
                .font(.system(size: 48))
                .foregroundStyle(.purple)
            Text("AI Satellite Assistant")
                .font(.title3.weight(.semibold))
            Text("Ask about pass quality, signal health, mission planning, or orbital mechanics.")
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            // Quick prompts
            VStack(spacing: 8) {
                ForEach(vm.quickPrompts, id: \.self) { prompt in
                    Button {
                        vm.inputText = prompt
                        Task { await vm.send() }
                    } label: {
                        Text(prompt)
                            .font(.callout)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(uiColor: .secondarySystemGroupedBackground),
                                        in: RoundedRectangle(cornerRadius: 10))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.top, 4)
        }
        .padding(.top, 40)
    }

    // MARK: – Input bar

    private var inputBar: some View {
        VStack(spacing: 0) {
            Divider()
            HStack(alignment: .bottom, spacing: 10) {
                TextField("Ask about the mission…", text: $vm.inputText, axis: .vertical)
                    .lineLimit(1...5)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(Color(uiColor: .secondarySystemGroupedBackground),
                                in: RoundedRectangle(cornerRadius: 20))
                    .focused($inputFocused)
                    .disabled(vm.isAtLimit || vm.isWaiting)
                    .onSubmit { sendMessage() }

                sendButton
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(Color(uiColor: .systemBackground))
        }
        .overlay(limitBanner, alignment: .top)
    }

    private var sendButton: some View {
        Button(action: sendMessage) {
            Group {
                if vm.isWaiting {
                    ProgressView().tint(.white).scaleEffect(0.8)
                } else {
                    Image(systemName: "arrow.up")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundStyle(.white)
                }
            }
            .frame(width: 36, height: 36)
            .background(sendButtonColor, in: Circle())
        }
        .disabled(vm.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                  || vm.isWaiting || vm.isAtLimit)
    }

    @ViewBuilder
    private var limitBanner: some View {
        if vm.isAtLimit {
            HStack {
                Image(systemName: "exclamationmark.circle")
                Text("Session limit reached. Reset to continue.")
            }
            .font(.caption)
            .foregroundStyle(.orange)
            .padding(.horizontal, 16)
            .padding(.vertical, 6)
            .background(.ultraThinMaterial)
            .clipShape(Capsule())
            .offset(y: -40)
        }
    }

    // MARK: – Helpers

    private var turnColor: Color {
        let ratio = Double(vm.turnCount) / Double(AppConfig.maxChatTurns)
        return ratio < 0.6 ? .green : ratio < 0.85 ? .orange : .red
    }

    private var sendButtonColor: Color {
        vm.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || vm.isAtLimit
            ? Color(uiColor: .systemGray3) : .purple
    }

    private func sendMessage() {
        guard !vm.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        inputFocused = false
        Task { await vm.send() }
    }
}
