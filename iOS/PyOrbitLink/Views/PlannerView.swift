import SwiftUI

struct PlannerView: View {

    @ObservedObject var vm: PlannerViewModel
    @FocusState private var inputFocused: Bool

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                header
                inputSection
                if vm.isProcessing { processingCard }
                if let result = vm.result { resultCard(result) }
                if let err = vm.errorMessage { errorCard(err) }
                examplesSection
            }
            .padding()
        }
        .background(Color(uiColor: .systemGroupedBackground))
    }

    // MARK: – Header

    private var header: some View {
        VStack(spacing: 8) {
            Image(systemName: "brain.head.profile")
                .font(.system(size: 36))
                .foregroundStyle(.orange)
            Text("Natural Language Planner")
                .font(.headline)
            Text("Describe what you want in plain English. The AI maps it to a mission function.")
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, 8)
    }

    // MARK: – Input

    private var inputSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            TextField("e.g. Find upcoming ISS passes for the next 2 days", text: $vm.inputText,
                      axis: .vertical)
                .lineLimit(2...4)
                .padding()
                .background(Color(uiColor: .secondarySystemGroupedBackground),
                            in: RoundedRectangle(cornerRadius: 14))
                .focused($inputFocused)

            Button {
                inputFocused = false
                Task { await vm.plan() }
            } label: {
                Label("Plan Mission", systemImage: "sparkles")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(vm.isProcessing ? Color.gray : Color.orange,
                                in: RoundedRectangle(cornerRadius: 14))
                    .foregroundStyle(.white)
            }
            .disabled(vm.isProcessing || vm.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
    }

    // MARK: – Processing card

    private var processingCard: some View {
        HStack(spacing: 14) {
            ProgressView().tint(.orange)
            Text("Parsing intent…")
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(Color(uiColor: .secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 14))
    }

    // MARK: – Result card

    private func resultCard(_ result: PlanResult) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Function call header
            HStack {
                Image(systemName: result.function != nil ? "checkmark.circle.fill" : "questionmark.circle")
                    .foregroundStyle(result.function != nil ? .green : .orange)
                Text(result.function != nil ? "Function Dispatched" : "Intent Unclear")
                    .font(.subheadline.weight(.semibold))
                Spacer()
            }

            if result.function != nil {
                // Code-style function call display
                Text(vm.functionCallText)
                    .font(.system(.callout, design: .monospaced))
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(uiColor: .systemGray6), in: RoundedRectangle(cornerRadius: 10))

                // Execution result
                if let execResult = result.result {
                    Divider()
                    Text("Result")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    execResultView(execResult)
                }
            }

            if let err = result.error {
                Label(err, systemImage: "exclamationmark.triangle")
                    .font(.callout)
                    .foregroundStyle(.red)
            }
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 16))
    }

    @ViewBuilder
    private func execResultView(_ r: PlanExecResult) -> some View {
        if let events = r.events, !events.isEmpty {
            VStack(spacing: 0) {
                ForEach(events.prefix(3)) { event in
                    PassEventRow(event: event)
                    Divider()
                }
            }
        } else {
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                if let az = r.azimuth   { miniStat("Azimuth",   String(format: "%.1f°", az),   .cyan) }
                if let el = r.elevation { miniStat("Elevation", String(format: "%.1f°", el),   .green) }
                if let rn = r.range     { miniStat("Range",     String(format: "%.0f km", rn), .orange) }
                if let fs = r.fspl      { miniStat("FSPL",      String(format: "%.1f dB", fs), .purple) }
            }
        }
    }

    private func miniStat(_ label: String, _ value: String, _ color: Color) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 18, weight: .bold, design: .rounded).monospacedDigit())
                .foregroundStyle(color)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(10)
        .background(color.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
    }

    // MARK: – Error card

    private func errorCard(_ message: String) -> some View {
        Label(message, systemImage: "exclamationmark.triangle.fill")
            .font(.callout)
            .foregroundStyle(.red)
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.red.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
    }

    // MARK: – Examples

    private var examplesSection: some View {
        CardView(title: "Example Prompts") {
            VStack(spacing: 8) {
                ForEach(vm.examplePrompts, id: \.self) { prompt in
                    Button {
                        vm.inputText = prompt
                    } label: {
                        HStack {
                            Image(systemName: "lightbulb").foregroundStyle(.orange)
                            Text(prompt).font(.callout).foregroundStyle(.primary)
                            Spacer()
                            Image(systemName: "chevron.right").foregroundStyle(.secondary).font(.caption)
                        }
                        .padding(.vertical, 8)
                    }
                    .buttonStyle(.plain)
                    if prompt != vm.examplePrompts.last { Divider() }
                }
            }
        }
    }
}
