import SwiftUI

// MARK: – Circular signal quality gauge

struct SignalGauge: View {

    let value: Double    // 0.0 – 1.0
    let label: String
    let color: Color

    @State private var animatedValue: Double = 0

    var body: some View {
        ZStack {
            // Background ring
            Circle()
                .stroke(Color(uiColor: .tertiarySystemBackground), lineWidth: 14)

            // Value arc
            Circle()
                .trim(from: 0, to: animatedValue)
                .stroke(
                    AngularGradient(
                        gradient: Gradient(colors: [color.opacity(0.6), color]),
                        center: .center,
                        startAngle: .degrees(-90),
                        endAngle:   .degrees(270)
                    ),
                    style: StrokeStyle(lineWidth: 14, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))

            // Centre content
            VStack(spacing: 2) {
                Text(String(format: "%.0f%%", animatedValue * 100))
                    .font(.system(size: 22, weight: .bold, design: .rounded).monospacedDigit())
                    .foregroundStyle(color)
                Text(label)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 60)
            }
        }
        .frame(width: 110, height: 110)
        .onAppear {
            withAnimation(.spring(duration: 1.0, bounce: 0.2)) {
                animatedValue = min(max(value, 0), 1)
            }
        }
        .onChange(of: value) { newValue in
            withAnimation(.spring(duration: 0.6)) {
                animatedValue = min(max(newValue, 0), 1)
            }
        }
    }
}

// MARK: – Mini bar signal strength indicator (5 bars)

struct SignalBars: View {

    let quality: Double   // 0.0 – 1.0
    let color: Color

    private let barCount = 5

    var body: some View {
        HStack(alignment: .bottom, spacing: 3) {
            ForEach(0..<barCount, id: \.self) { i in
                let threshold = Double(i + 1) / Double(barCount)
                let isActive  = quality >= threshold - 0.1
                RoundedRectangle(cornerRadius: 2)
                    .fill(isActive ? color : color.opacity(0.2))
                    .frame(width: 6, height: CGFloat(8 + i * 5))
                    .animation(.easeInOut(duration: 0.3), value: isActive)
            }
        }
    }
}

// MARK: – Elevation arc indicator

struct ElevationArc: View {

    let elevation: Double   // 0–90°

    var body: some View {
        ZStack {
            // Background semicircle
            SemicircleShape()
                .stroke(Color(uiColor: .tertiarySystemBackground), lineWidth: 10)

            // Active arc
            SemicircleShape()
                .trim(from: 0, to: elevation / 90)
                .stroke(
                    LinearGradient(colors: [.red, .orange, .green],
                                   startPoint: .leading, endPoint: .trailing),
                    style: StrokeStyle(lineWidth: 10, lineCap: .round)
                )

            // Label
            VStack(spacing: 0) {
                Spacer()
                Text(String(format: "%.1f°", elevation))
                    .font(.system(size: 14, weight: .bold, design: .rounded).monospacedDigit())
                Text("Elevation")
                    .font(.system(size: 9))
                    .foregroundStyle(.secondary)
            }
            .padding(.bottom, 4)
        }
        .frame(width: 100, height: 55)
    }
}

private struct SemicircleShape: Shape {
    func path(in rect: CGRect) -> Path {
        Path { path in
            path.addArc(center: CGPoint(x: rect.midX, y: rect.maxY),
                        radius: rect.width / 2,
                        startAngle: .degrees(180),
                        endAngle:   .degrees(0),
                        clockwise: false)
        }
    }
}
