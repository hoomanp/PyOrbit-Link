import SwiftUI
import MapKit

// MARK: – MapKit view showing observer + satellite position

struct SatelliteMapView: View {

    let snapshot: TelemetrySnapshot?
    let observerCoordinate: CLLocationCoordinate2D?

    @State private var mapPosition: MapCameraPosition = .automatic
    @State private var isFollowing: Bool = true

    var body: some View {
        Map(position: $mapPosition) {
            // Observer marker (device GPS)
            if let coord = observerCoordinate {
                Annotation("Observer", coordinate: coord) {
                    ZStack {
                        Circle()
                            .fill(.blue.opacity(0.2))
                            .frame(width: 40, height: 40)
                        Image(systemName: "antenna.radiowaves.left.and.right")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(.blue)
                    }
                }

                // Accuracy circle — radius not natively supported in annotation,
                // so we use a MapCircle overlay
            }

            // Satellite position
            if let snap = snapshot {
                let satCoord = snap.approximateSatelliteCoordinate
                Annotation("ISS", coordinate: satCoord) {
                    ZStack {
                        Circle()
                            .fill(snap.isVisible ? Color.cyan.opacity(0.2) : Color.gray.opacity(0.15))
                            .frame(width: 44, height: 44)
                        Image(systemName: "dot.radiowaves.right")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(snap.isVisible ? .cyan : .gray)
                            .symbolEffect(.variableColor.iterative.dimInactiveLayers, value: snap.isVisible)
                    }
                }

                // Link-of-sight line
                if let obs = observerCoordinate {
                    MapPolyline(coordinates: [obs, satCoord])
                        .stroke(snap.isVisible ? .cyan.opacity(0.6) : .gray.opacity(0.3),
                                style: StrokeStyle(lineWidth: 2, dash: [5, 5]))
                }

                // Approximate footprint circle (rough: 2500 km for LEO)
                MapCircle(center: satCoord, radius: 2_500_000)
                    .foregroundStyle(.cyan.opacity(0.05))
                    .stroke(.cyan.opacity(0.15), lineWidth: 1)
            }
        }
        .mapControls {
            MapCompass()
            MapScaleView()
            MapUserLocationButton()
        }
        .mapStyle(.imagery(elevation: .realistic))
        .overlay(alignment: .topTrailing) { followButton }
        .onChange(of: snapshot) { newSnap in
            guard isFollowing, let snap = newSnap, let obs = observerCoordinate else { return }
            // Fit both observer and satellite in frame
            let centre = CLLocationCoordinate2D(
                latitude:  (obs.latitude  + snap.approximateSatelliteCoordinate.latitude)  / 2,
                longitude: (obs.longitude + snap.approximateSatelliteCoordinate.longitude) / 2
            )
            withAnimation(.easeInOut(duration: 1.0)) {
                mapPosition = .region(
                    MKCoordinateRegion(center: centre,
                                       latitudinalMeters:  3_000_000,
                                       longitudinalMeters: 3_000_000)
                )
            }
        }
        .onAppear {
            if let obs = observerCoordinate {
                mapPosition = .region(
                    MKCoordinateRegion(center: obs,
                                       latitudinalMeters: 2_000_000,
                                       longitudinalMeters: 2_000_000)
                )
            }
        }
    }

    private var followButton: some View {
        Button {
            isFollowing.toggle()
        } label: {
            Image(systemName: isFollowing ? "location.fill" : "location")
                .padding(8)
                .background(.ultraThinMaterial, in: Circle())
        }
        .padding(8)
    }
}
