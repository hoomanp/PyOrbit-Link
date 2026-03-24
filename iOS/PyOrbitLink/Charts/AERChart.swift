import SwiftUI
import Charts

// MARK: – Azimuth / Elevation / Range chart (3 series, iOS 16+ Swift Charts)

struct AERChart: View {

    let history: [TelemetrySnapshot]

    private enum Series: String, CaseIterable {
        case elevation = "Elevation (°)"
        case azimuth   = "Azimuth (°)"
        case range     = "Range (km)"
    }

    var body: some View {
        if history.isEmpty {
            emptyState
        } else {
            chart
        }
    }

    private var chart: some View {
        Chart {
            ForEach(history) { snap in
                // Elevation line (primary axis, 0–90°)
                LineMark(
                    x: .value("Time",      snap.timestamp),
                    y: .value("Elevation", snap.elevation),
                    series: .value("Series", Series.elevation.rawValue)
                )
                .foregroundStyle(.cyan)
                .interpolationMethod(.catmullRom)

                // Horizon reference line at 5°
                RuleMark(y: .value("Horizon", 5.0))
                    .foregroundStyle(.red.opacity(0.3))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
                    .annotation(position: .trailing) {
                        Text("Horizon")
                            .font(.system(size: 8))
                            .foregroundStyle(.red.opacity(0.6))
                    }

                // FSPL as AreaMark on secondary axis (mapped to 0–90 range)
                AreaMark(
                    x: .value("Time", snap.timestamp),
                    y: .value("Link",  snap.linkQuality * 90)
                )
                .foregroundStyle(
                    LinearGradient(colors: [.green.opacity(0.3), .clear],
                                   startPoint: .top, endPoint: .bottom)
                )
                .interpolationMethod(.catmullRom)
            }
        }
        .chartXAxis {
            AxisMarks(values: .automatic(desiredCount: 4)) { value in
                AxisGridLine()
                AxisValueLabel(format: .dateTime.hour().minute().second())
                    .font(.system(size: 9))
            }
        }
        .chartYAxis {
            AxisMarks(position: .leading, values: .automatic(desiredCount: 5)) { value in
                AxisGridLine()
                AxisValueLabel { if let v = value.as(Double.self) { Text("\(Int(v))°") } }
            }
        }
        .chartLegend(position: .top, alignment: .leading, spacing: 8) {
            HStack(spacing: 12) {
                legendDot(.cyan,   "Elevation")
                legendDot(.green,  "Link Quality")
                legendLine(.red.opacity(0.5), "Horizon")
            }
            .font(.caption2)
        }
        .frame(height: 180)
        .padding(.horizontal, 4)
    }

    private var emptyState: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(Color(uiColor: .secondarySystemBackground))
            .frame(height: 180)
            .overlay {
                VStack(spacing: 8) {
                    Image(systemName: "satellite.dish")
                        .font(.title2)
                        .foregroundStyle(.secondary)
                    Text("Awaiting telemetry…")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
    }

    private func legendDot(_ color: Color, _ label: String) -> some View {
        HStack(spacing: 4) {
            Circle().fill(color).frame(width: 8, height: 8)
            Text(label).foregroundStyle(.secondary)
        }
    }

    private func legendLine(_ color: Color, _ label: String) -> some View {
        HStack(spacing: 4) {
            Rectangle().fill(color).frame(width: 16, height: 2)
            Text(label).foregroundStyle(.secondary)
        }
    }
}

// MARK: – Polar sky-view (azimuth vs elevation polar plot)

struct PolarSkyView: View {

    let history: [PolarPoint]

    var body: some View {
        GeometryReader { geo in
            let size   = min(geo.size.width, geo.size.height)
            let centre = CGPoint(x: geo.size.width / 2, y: geo.size.height / 2)
            let radius = size / 2 - 8

            ZStack {
                // Concentric rings (0°, 30°, 60°, 90°)
                ForEach([0, 30, 60, 90], id: \.self) { el in
                    let r = radius * (1.0 - Double(el) / 90.0)
                    Circle()
                        .stroke(Color.primary.opacity(0.12), lineWidth: 0.5)
                        .frame(width: r * 2, height: r * 2)
                        .position(centre)
                    Text("\(el)°")
                        .font(.system(size: 8))
                        .foregroundStyle(.secondary)
                        .position(x: centre.x + 4, y: centre.y - r)
                }

                // N / E / S / W labels
                cardinalLabel("N", offset: CGPoint(x: 0,      y: -radius - 12), centre: centre)
                cardinalLabel("E", offset: CGPoint(x: radius + 12,  y: 0),      centre: centre)
                cardinalLabel("S", offset: CGPoint(x: 0,      y:  radius + 12), centre: centre)
                cardinalLabel("W", offset: CGPoint(x: -radius - 12, y: 0),      centre: centre)

                // Pass track
                if history.count > 1 {
                    Path { path in
                        let pts = history.map { polarToCartesian($0, centre: centre, radius: radius) }
                        path.move(to: pts[0])
                        pts.dropFirst().forEach { path.addLine(to: $0) }
                    }
                    .stroke(
                        LinearGradient(colors: [.cyan.opacity(0.3), .cyan],
                                       startPoint: .leading, endPoint: .trailing),
                        style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round)
                    )
                }

                // Latest position dot
                if let last = history.last {
                    let pt = polarToCartesian(last, centre: centre, radius: radius)
                    Circle()
                        .fill(Color.cyan)
                        .frame(width: 10, height: 10)
                        .position(pt)
                    Circle()
                        .stroke(Color.cyan.opacity(0.4), lineWidth: 6)
                        .frame(width: 10, height: 10)
                        .position(pt)
                }
            }
        }
        .aspectRatio(1, contentMode: .fit)
    }

    private func polarToCartesian(_ p: PolarPoint, centre: CGPoint, radius: Double) -> CGPoint {
        let el  = min(max(p.elevation, 0), 90)
        let r   = radius * (1.0 - el / 90.0)
        let az  = p.azimuth * .pi / 180
        return CGPoint(x: centre.x + r * sin(az),
                       y: centre.y - r * cos(az))
    }

    private func cardinalLabel(_ text: String, offset: CGPoint, centre: CGPoint) -> some View {
        Text(text)
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(.secondary)
            .position(x: centre.x + offset.x, y: centre.y + offset.y)
    }
}
