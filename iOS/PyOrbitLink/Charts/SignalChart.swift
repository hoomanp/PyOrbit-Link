import SwiftUI
import Charts

// MARK: – Rolling signal quality chart (link quality 0–1 over time)

struct SignalQualityChart: View {

    let readings: [SignalReading]

    var body: some View {
        if readings.isEmpty {
            placeholderBar
        } else {
            chart
        }
    }

    private var chart: some View {
        Chart {
            ForEach(readings) { r in
                AreaMark(
                    x: .value("Time",    r.timestamp),
                    y: .value("Quality", r.linkQuality * 100)
                )
                .foregroundStyle(
                    LinearGradient(
                        colors: [qualityColor(r.linkQuality).opacity(0.7),
                                 qualityColor(r.linkQuality).opacity(0.1)],
                        startPoint: .top, endPoint: .bottom
                    )
                )
                .interpolationMethod(.catmullRom)

                LineMark(
                    x: .value("Time",    r.timestamp),
                    y: .value("Quality", r.linkQuality * 100)
                )
                .foregroundStyle(qualityColor(r.linkQuality))
                .interpolationMethod(.catmullRom)
            }

            // Quality threshold lines
            RuleMark(y: .value("Good",      60)).foregroundStyle(.green.opacity(0.25))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [3, 3]))
            RuleMark(y: .value("Fair",      40)).foregroundStyle(.yellow.opacity(0.25))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [3, 3]))
        }
        .chartYScale(domain: 0...100)
        .chartXAxis {
            AxisMarks(values: .automatic(desiredCount: 4)) {
                AxisGridLine()
                AxisValueLabel(format: .dateTime.minute().second())
                    .font(.system(size: 9))
            }
        }
        .chartYAxis {
            AxisMarks(position: .leading, values: [0, 25, 50, 75, 100]) { value in
                AxisGridLine()
                AxisValueLabel(value.as(Double.self).map { "\(Int($0))%" } ?? "")
            }
        }
        .frame(height: 160)
    }

    private func qualityColor(_ q: Double) -> Color {
        switch q {
        case 0.8...: return .green
        case 0.6..<0.8: return .mint
        case 0.4..<0.6: return .yellow
        case 0.2..<0.4: return .orange
        default:        return .red
        }
    }

    private var placeholderBar: some View {
        RoundedRectangle(cornerRadius: 10)
            .fill(Color(uiColor: .secondarySystemBackground))
            .frame(height: 160)
            .overlay { Text("Collecting signal data…").font(.caption).foregroundStyle(.secondary) }
    }
}

// MARK: – GPS accuracy over time

struct GPSAccuracyChart: View {

    let history: [(time: Date, accuracy: Double)]

    var body: some View {
        Chart {
            ForEach(Array(history.enumerated()), id: \.offset) { _, point in
                AreaMark(
                    x: .value("Time",     point.time),
                    y: .value("Accuracy", point.accuracy)
                )
                .foregroundStyle(
                    LinearGradient(colors: [.blue.opacity(0.5), .blue.opacity(0.05)],
                                   startPoint: .top, endPoint: .bottom)
                )
                LineMark(
                    x: .value("Time",     point.time),
                    y: .value("Accuracy", point.accuracy)
                )
                .foregroundStyle(.blue)
            }

            // Target: <10 m high-accuracy zone
            RuleMark(y: .value("High Accuracy", 10))
                .foregroundStyle(.green.opacity(0.4))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                .annotation(position: .trailing) {
                    Text("10 m").font(.system(size: 8)).foregroundStyle(.green)
                }
        }
        .chartXAxis {
            AxisMarks(values: .automatic(desiredCount: 4)) {
                AxisGridLine()
                AxisValueLabel(format: .dateTime.minute().second()).font(.system(size: 9))
            }
        }
        .chartYAxis {
            AxisMarks(position: .leading, values: .automatic(desiredCount: 4)) { value in
                AxisGridLine()
                AxisValueLabel(value.as(Double.self).map { "\(Int($0)) m" } ?? "")
            }
        }
        .frame(height: 130)
    }
}
