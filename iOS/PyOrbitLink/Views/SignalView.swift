import SwiftUI

struct SignalView: View {

    @ObservedObject var vm: SignalViewModel
    @EnvironmentObject private var locationService: LocationService
    @EnvironmentObject private var signalService:   SignalMonitorService

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                gaugeRow
                networkInfoCard
                signalHistoryCard
                gpsCard
                linkBudgetMiniCard
            }
            .padding()
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .onAppear { vm.startCollecting() }
        .onDisappear { vm.stopCollecting() }
        // Feed latest telemetry into signal ViewModel (normally wired from LiveTrackVM)
        .onChange(of: vm.latestReading) { _ in }
    }

    // MARK: – Gauge row

    private var gaugeRow: some View {
        HStack(spacing: 20) {
            SignalGauge(
                value: vm.latestReading?.linkQuality ?? 0,
                label: "Link\nQuality",
                color: vm.latestReading?.linkQualityColor ?? .gray
            )

            VStack(spacing: 14) {
                ElevationArc(elevation: vm.latestReading?.elevation ?? 0)
                Text(vm.latestReading?.linkQualityLabel ?? "No Data")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(vm.latestReading?.linkQualityColor ?? .gray)
            }

            VStack(alignment: .leading, spacing: 8) {
                radioRow
                gpsRow
            }
        }
        .padding()
        .background(Color(uiColor: .secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: – Network info card

    private var networkInfoCard: some View {
        CardView(title: "Device Radio") {
            VStack(spacing: 0) {
                InfoRow(label: "Network Type",
                        value: signalService.radioTechnology.rawValue,
                        icon:  signalService.radioTechnology.icon,
                        color: signalService.radioTechnology.color)
                Divider().padding(.leading, 40)
                InfoRow(label: "Carrier",
                        value: signalService.carrierName ?? "N/A",
                        icon:  "building.2",
                        color: .blue)
                Divider().padding(.leading, 40)
                InfoRow(label: "Connection",
                        value: signalService.interfaceType,
                        icon:  signalService.isOnWiFi ? "wifi" : "antenna.radiowaves.left.and.right",
                        color: signalService.isConnected ? .green : .red)
                Divider().padding(.leading, 40)
                InfoRow(label: "GPS Accuracy",
                        value: vm.gpsAccuracyText,
                        icon:  "location.fill",
                        color: gpsColor)
            }
        }
    }

    // MARK: – Signal history chart

    private var signalHistoryCard: some View {
        CardView(title: "Link Quality — \(AppConfig.signalHistorySeconds)s Rolling") {
            SignalQualityChart(readings: vm.readings)
        }
    }

    // MARK: – GPS card

    private var gpsCard: some View {
        CardView(title: "GPS Signal") {
            VStack(spacing: 12) {
                GPSAccuracyChart(history: vm.gpsAccuracyHistory)

                HStack(spacing: 20) {
                    gpsMetric(label: "Latitude",
                              value: locationService.coordinate.map { String(format: "%.5f°", $0.latitude) } ?? "—")
                    gpsMetric(label: "Longitude",
                              value: locationService.coordinate.map { String(format: "%.5f°", $0.longitude) } ?? "—")
                    gpsMetric(label: "Altitude",
                              value: locationService.altitude.map { String(format: "%.0f m", $0) } ?? "—")
                }
            }
        }
    }

    // MARK: – Link budget mini

    private var linkBudgetMiniCard: some View {
        CardView(title: "FSPL Trend") {
            if vm.fsplHistory.isEmpty {
                Text("No FSPL data yet")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, minHeight: 80, alignment: .center)
            } else {
                FSPLTrendChart(history: vm.fsplHistory)
                HStack {
                    if let last = vm.latestReading?.fspl {
                        Label(String(format: "%.1f dB", last), systemImage: "waveform.path")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.orange)
                    }
                    Spacer()
                    if let el = vm.latestReading?.elevation {
                        Label(String(format: "%.1f°", el), systemImage: "arrow.up.circle")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.cyan)
                    }
                }
            }
        }
    }

    // MARK: – Sub-components

    private var radioRow: some View {
        HStack(spacing: 6) {
            Image(systemName: signalService.radioTechnology.icon)
                .foregroundStyle(signalService.radioTechnology.color)
                .frame(width: 18)
            SignalBars(quality: signalService.isConnected ? 0.8 : 0.1,
                       color: signalService.radioTechnology.color)
        }
    }

    private var gpsRow: some View {
        HStack(spacing: 6) {
            Image(systemName: "location.fill")
                .foregroundStyle(gpsColor)
                .frame(width: 18)
            let cat = GPSAccuracy(locationService.accuracy)
            Text(cat.label)
                .font(.caption2)
                .foregroundStyle(gpsColor)
        }
    }

    private var gpsColor: Color {
        GPSAccuracy(locationService.accuracy).color
    }

    private func gpsMetric(label: String, value: String) -> some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(size: 13, weight: .semibold, design: .monospaced))
                .minimumScaleFactor(0.7)
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: – Generic info row

struct InfoRow: View {
    let label: String
    let value: String
    let icon:  String
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(color)
                .frame(width: 22, height: 22)
            Text(label)
                .font(.callout)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.callout.weight(.medium))
                .foregroundStyle(.primary)
        }
        .padding(.vertical, 10)
    }
}
