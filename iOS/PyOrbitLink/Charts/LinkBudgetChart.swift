import SwiftUI
import Charts

// MARK: – Link Budget bar chart

struct LinkBudgetChart: View {

    struct BudgetComponent: Identifiable {
        let id    = UUID()
        let name  : String
        let value : Double   // dB
        let isLoss: Bool
    }

    let fspl      : Double    // Free-space path loss (dB)
    let elevation : Double    // Degrees (drives atmospheric loss estimate)

    private var components: [BudgetComponent] {
        let atmosphericLoss = max(0, (10 - elevation) * 0.05)   // crude estimate
        let pointingLoss    = elevation < 15 ? (15 - elevation) * 0.3 : 0.0
        let txPower         = 10.0     // dBW typical ground station
        let txGain          = 6.0      // dBi
        let rxGain          = 2.0      // dBi (phone/antenna)
        let rxNoise         = -130.0   // dBW receiver noise floor

        return [
            BudgetComponent(name: "Tx Power",       value: txPower,         isLoss: false),
            BudgetComponent(name: "Tx Gain",         value: txGain,          isLoss: false),
            BudgetComponent(name: "Rx Gain",         value: rxGain,          isLoss: false),
            BudgetComponent(name: "FSPL",            value: -fspl,           isLoss: true),
            BudgetComponent(name: "Atm. Loss",       value: -atmosphericLoss, isLoss: true),
            BudgetComponent(name: "Pointing Loss",   value: -pointingLoss,   isLoss: true),
        ]
    }

    var linkMargin: Double {
        components.reduce(0) { $0 + $1.value }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Margin summary
            HStack {
                Text("Link Margin")
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text(String(format: "%.1f dB", linkMargin))
                    .font(.title3.weight(.bold).monospacedDigit())
                    .foregroundStyle(linkMarginColor)
            }

            Chart(components) { c in
                BarMark(
                    x: .value("Name",  c.name),
                    y: .value("Value", c.value)
                )
                .foregroundStyle(c.isLoss ? Color.red : Color.green)
                .cornerRadius(4)
                .annotation(position: c.value >= 0 ? .top : .bottom) {
                    Text(String(format: "%.1f", c.value))
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
            }
            .chartXAxis {
                AxisMarks { value in
                    AxisValueLabel(value.as(String.self) ?? "")
                        .font(.system(size: 9))
                }
            }
            .chartYAxis {
                AxisMarks(position: .leading, values: .automatic(desiredCount: 5)) { value in
                    AxisGridLine()
                    AxisValueLabel(value.as(Double.self).map { "\(Int($0))" } ?? "")
                }
            }
            .frame(height: 170)
        }
    }

    private var linkMarginColor: Color {
        switch linkMargin {
        case 10...:    return .green
        case 3..<10:   return .yellow
        case 0..<3:    return .orange
        default:       return .red
        }
    }
}

// MARK: – FSPL Trend mini chart

struct FSPLTrendChart: View {

    let history: [(time: Date, fspl: Double)]

    var body: some View {
        Chart {
            ForEach(Array(history.enumerated()), id: \.offset) { _, point in
                LineMark(
                    x: .value("Time", point.time),
                    y: .value("FSPL", point.fspl)
                )
                .foregroundStyle(.orange)
                .interpolationMethod(.catmullRom)
            }
        }
        .chartXAxis(.hidden)
        .chartYAxis {
            AxisMarks(position: .trailing, values: .automatic(desiredCount: 3)) { value in
                AxisGridLine()
                AxisValueLabel(value.as(Double.self).map { "\(Int($0)) dB" } ?? "")
                    .font(.system(size: 9))
            }
        }
        .frame(height: 80)
    }
}
