import SwiftUI

struct AlertsView: View {

    @ObservedObject var vm: AlertsViewModel
    @State private var showCriticalOnly = false

    var displayedAlerts: [AnomalyAlert] {
        showCriticalOnly
            ? vm.alerts.filter { $0.severity == .critical }
            : vm.alerts
    }

    var body: some View {
        Group {
            if vm.alerts.isEmpty && !vm.isPolling {
                emptyState
            } else {
                alertList
            }
        }
        .toolbar { toolbarContent }
        .onAppear {
            vm.startPolling()
            vm.markAllRead()
        }
        .onDisappear { vm.stopPolling() }
        .refreshable { vm.refresh() }
        .overlay(errorBanner, alignment: .bottom)
    }

    // MARK: – Alert list

    private var alertList: some View {
        List {
            Section {
                filterToggle
            }

            if displayedAlerts.isEmpty {
                Text("No \(showCriticalOnly ? "critical " : "")alerts recorded.")
                    .foregroundStyle(.secondary)
                    .font(.callout)
                    .listRowBackground(Color.clear)
            } else {
                ForEach(displayedAlerts) { alert in
                    AlertRow(alert: alert)
                        .listRowBackground(alert.severity.color.opacity(0.06))
                        .listRowInsets(.init(top: 0, leading: 0, bottom: 0, trailing: 0))
                }
            }
        }
        .listStyle(.insetGrouped)
    }

    // MARK: – Empty state

    private var emptyState: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.shield.fill")
                .font(.system(size: 56))
                .foregroundStyle(.green)
                .symbolEffect(.pulse)
            Text("No Anomalies Detected")
                .font(.title3.weight(.semibold))
            Text("The AI anomaly monitor is watching satellite telemetry in real time. Alerts appear here when thresholds are exceeded.")
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            if let updated = vm.lastUpdated {
                Text("Last checked: \(updated, style: .relative) ago")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding()
    }

    // MARK: – Filter toggle

    private var filterToggle: some View {
        Toggle(isOn: $showCriticalOnly) {
            Label("Critical Only", systemImage: "xmark.octagon.fill")
                .foregroundStyle(showCriticalOnly ? .red : .primary)
        }
    }

    // MARK: – Error banner

    @ViewBuilder
    private var errorBanner: some View {
        if let err = vm.errorMessage {
            Label(err, systemImage: "wifi.slash")
                .font(.caption)
                .foregroundStyle(.white)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(.red, in: Capsule())
                .shadow(radius: 4)
                .padding(.bottom, 16)
                .transition(.move(edge: .bottom).combined(with: .opacity))
        }
    }

    // MARK: – Toolbar

    private var toolbarContent: some ToolbarContent {
        ToolbarItemGroup(placement: .navigationBarTrailing) {
            if vm.isPolling {
                ProgressView().scaleEffect(0.8)
            }
            if let updated = vm.lastUpdated {
                Text(updated, style: .relative)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

// MARK: – Alert row

struct AlertRow: View {

    let alert: AnomalyAlert
    @State private var isExpanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            Button {
                withAnimation(.easeInOut(duration: 0.25)) { isExpanded.toggle() }
                UIImpactFeedbackGenerator(style: .light).impactOccurred()
            } label: {
                HStack(spacing: 14) {
                    // Severity icon
                    ZStack {
                        RoundedRectangle(cornerRadius: 10)
                            .fill(alert.severity.color.opacity(0.15))
                            .frame(width: 44, height: 44)
                        Image(systemName: alert.severity.icon)
                            .font(.system(size: 20))
                            .foregroundStyle(alert.severity.color)
                    }

                    VStack(alignment: .leading, spacing: 3) {
                        HStack {
                            Text(alert.severity.label)
                                .font(.caption.weight(.bold))
                                .foregroundStyle(alert.severity.color)
                            Spacer()
                            Text(alert.formattedTime)
                                .font(.caption2.monospacedDigit())
                                .foregroundStyle(.secondary)
                        }
                        Text(alert.explanation)
                            .font(.callout)
                            .foregroundStyle(.primary)
                            .lineLimit(isExpanded ? nil : 2)
                            .multilineTextAlignment(.leading)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
            .buttonStyle(.plain)

            // Expanded detail
            if isExpanded {
                VStack(alignment: .leading, spacing: 8) {
                    Divider().padding(.horizontal, 16)
                    HStack {
                        Label("Full AI Explanation", systemImage: "text.bubble")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                        Spacer()
                        Button {
                            UIPasteboard.general.string = alert.explanation
                        } label: {
                            Image(systemName: "doc.on.clipboard")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.horizontal, 16)

                    Text(alert.explanation)
                        .font(.callout)
                        .foregroundStyle(.primary)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 12)
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }
}
