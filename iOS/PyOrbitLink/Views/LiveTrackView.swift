import SwiftUI
import CoreLocation

struct LiveTrackView: View {

    @ObservedObject var vm: LiveTrackViewModel
    @EnvironmentObject private var locationService: LocationService
    @Environment(\.horizontalSizeClass) private var hSizeClass
    @State private var selectedPanel: Panel = .map

    enum Panel: String, CaseIterable {
        case map    = "Map"
        case aer    = "AER Chart"
        case polar  = "Sky View"
        case budget = "Link Budget"
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                statusBar
                panelPicker
                selectedPanelView
                telemetryCards
                aiAnalysis
                passEvents
            }
            .padding()
            .frame(maxWidth: hSizeClass == .regular ? 800 : .infinity)
            .frame(maxWidth: .infinity)
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .toolbar { streamToolbarButton }
        .onAppear {
            vm.refreshPassEvents()
            if vm.streamState == .idle { vm.startStream() }
        }
        .onDisappear { vm.stopStream() }
        .alert("Stream Error", isPresented: .constant(vm.errorMessage != nil)) {
            Button("Retry") { vm.startStream() }
            Button("Dismiss", role: .cancel) { }
        } message: {
            Text(vm.errorMessage ?? "")
        }
    }

    // MARK: – Status bar

    private var statusBar: some View {
        HStack(spacing: 10) {
            Circle()
                .fill(statusColor)
                .frame(width: 10, height: 10)
                .shadow(color: statusColor, radius: 4)
            Text(statusLabel)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)
            Spacer()
            if let snap = vm.latestSnapshot {
                Label(String(format: "El %.1f°", snap.elevation), systemImage: "arrow.up.right")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(snap.isVisible ? .cyan : .secondary)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    // MARK: – Panel picker

    private var panelPicker: some View {
        Picker("Panel", selection: $selectedPanel) {
            ForEach(Panel.allCases, id: \.self) { Text($0.rawValue).tag($0) }
        }
        .pickerStyle(.segmented)
    }

    // MARK: – Selected panel

    @ViewBuilder
    private var selectedPanelView: some View {
        switch selectedPanel {
        case .map:
            SatelliteMapView(snapshot: vm.latestSnapshot,
                             observerCoordinate: locationService.coordinate)
                .frame(height: 280)
                .clipShape(RoundedRectangle(cornerRadius: 16))
                .shadow(color: .black.opacity(0.15), radius: 8, y: 4)

        case .aer:
            CardView(title: "Azimuth / Elevation / Link Quality") {
                AERChart(history: vm.aerHistory)
            }

        case .polar:
            CardView(title: "Sky View") {
                PolarSkyView(history: vm.polarHistory)
                    .frame(height: 200)
                    .padding()
            }

        case .budget:
            if let snap = vm.latestSnapshot {
                CardView(title: "Link Budget") {
                    LinkBudgetChart(fspl: snap.fspl, elevation: snap.elevation)
                        .padding(.horizontal, 4)
                }
            } else {
                CardView(title: "Link Budget") {
                    Text("Awaiting first telemetry frame…")
                        .foregroundStyle(.secondary)
                        .font(.callout)
                        .frame(maxWidth: .infinity, minHeight: 120, alignment: .center)
                }
            }
        }
    }

    // MARK: – Telemetry cards

    private var telemetryCards: some View {
        let cols = hSizeClass == .regular ? 4 : 2
        return LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: cols), spacing: 12) {
            TelemetryCard(title: "Azimuth",   value: vm.latestSnapshot.map { String(format: "%.1f°", $0.azimuth) }   ?? "—", icon: "safari",           color: .cyan)
            TelemetryCard(title: "Elevation", value: vm.latestSnapshot.map { String(format: "%.1f°", $0.elevation) } ?? "—", icon: "arrow.up.circle",   color: .green)
            TelemetryCard(title: "Range",     value: vm.latestSnapshot.map { String(format: "%.0f km", $0.range) }   ?? "—", icon: "ruler",              color: .orange)
            TelemetryCard(title: "FSPL",      value: vm.latestSnapshot.map { String(format: "%.1f dB", $0.fspl) }    ?? "—", icon: "waveform.path",      color: .purple)
        }
    }

    // MARK: – AI analysis

    private var aiAnalysis: some View {
        CardView(title: "AI Analysis") {
            if vm.aiText.isEmpty && vm.streamState == .idle {
                Text("Start stream to receive AI analysis.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            } else {
                StreamingText(
                    text:        vm.aiText,
                    isStreaming: vm.streamState == .streaming || vm.streamState == .connecting,
                    font:        .callout,
                    color:       .primary
                )
            }
        }
    }

    // MARK: – Pass events

    @ViewBuilder
    private var passEvents: some View {
        if !vm.passEvents.isEmpty {
            CardView(title: "Upcoming Passes") {
                VStack(spacing: 0) {
                    ForEach(vm.passEvents.prefix(3)) { event in
                        PassEventRow(event: event)
                        if event.id != vm.passEvents.prefix(3).last?.id {
                            Divider().padding(.leading, 16)
                        }
                    }
                }
            }
        }
    }

    // MARK: – Toolbar

    private var streamToolbarButton: some ToolbarContent {
        ToolbarItem(placement: .navigationBarTrailing) {
            Button {
                if vm.streamState == .streaming || vm.streamState == .connecting {
                    vm.stopStream()
                } else {
                    vm.startStream()
                }
            } label: {
                Image(systemName: vm.streamState == .streaming ? "stop.circle.fill" : "play.circle.fill")
                    .foregroundStyle(vm.streamState == .streaming ? .red : .green)
            }
        }
    }

    // MARK: – Helpers

    private var statusColor: Color {
        switch vm.streamState {
        case .connecting: return .yellow
        case .streaming:  return .green
        case .done:       return .blue
        case .error:      return .red
        case .idle:       return .gray
        }
    }

    private var statusLabel: String {
        switch vm.streamState {
        case .connecting: return "Connecting…"
        case .streaming:  return "Live"
        case .done:       return "Complete"
        case .error:      return "Error"
        case .idle:       return "Idle"
        }
    }
}

// MARK: – Reusable card

struct CardView<Content: View>: View {
    let title: String
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)
            content()
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: – Telemetry metric card

struct TelemetryCard: View {
    let title: String
    let value: String
    let icon : String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: icon).foregroundStyle(color)
                Spacer()
            }
            Text(value)
                .font(.system(size: 22, weight: .bold, design: .rounded).monospacedDigit())
                .minimumScaleFactor(0.6)
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(14)
        .background(Color(uiColor: .secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 14))
    }
}

// MARK: – Pass event row

struct PassEventRow: View {
    let event: PassEvent

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("Rise").font(.caption2).foregroundStyle(.secondary)
                Text(formattedTime(event.rise)).font(.caption.monospacedDigit())
            }
            Spacer()
            Image(systemName: "arrow.up.circle").foregroundStyle(.cyan).font(.caption)
            Spacer()
            VStack(alignment: .center, spacing: 2) {
                Text("Max").font(.caption2).foregroundStyle(.secondary)
                Text(formattedTime(event.culmination)).font(.caption.monospacedDigit())
            }
            Spacer()
            Image(systemName: "arrow.down.circle").foregroundStyle(.orange).font(.caption)
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text("Set").font(.caption2).foregroundStyle(.secondary)
                Text(formattedTime(event.set)).font(.caption.monospacedDigit())
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 16)
    }

    private func formattedTime(_ iso: String) -> String {
        guard let d = ISO8601DateFormatter().date(from: iso) else { return iso }
        let f = DateFormatter()
        f.timeStyle = .short
        f.dateStyle = .short
        return f.string(from: d)
    }
}
