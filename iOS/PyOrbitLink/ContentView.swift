import SwiftUI

struct ContentView: View {

    @EnvironmentObject private var locationService: LocationService
    @EnvironmentObject private var signalService:   SignalMonitorService
    @EnvironmentObject private var settings:        AppSettings

    @StateObject private var liveTrackVM = LiveTrackViewModel()
    @StateObject private var signalVM    = SignalViewModel()
    @StateObject private var chatVM      = ChatViewModel()
    @StateObject private var plannerVM   = PlannerViewModel()
    @StateObject private var alertsVM    = AlertsViewModel()

    @State private var selectedTab: Tab = .liveTrack

    enum Tab: Int, CaseIterable {
        case liveTrack, signal, chat, planner, alerts

        var title:       String { ["Live Track","Signal","AI Chat","Planner","Alerts"][rawValue] }
        var icon:        String { ["satellite.dish","waveform","message.fill","map.fill","exclamationmark.triangle.fill"][rawValue] }
        var activeColor: Color  { [.cyan, .green, .purple, .orange, .red][rawValue] }
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            ForEach(Tab.allCases, id: \.self) { tab in
                tabContent(for: tab)
                    .tabItem {
                        Label(tab.title, systemImage: tab.icon)
                    }
                    .tag(tab)
            }
        }
        .tint(selectedTab.activeColor)
        .onAppear {
            wireViewModels()
        }
        .onChange(of: selectedTab) { _ in
            impactFeedback()
        }
    }

    // MARK: – Tab content routing

    @ViewBuilder
    private func tabContent(for tab: Tab) -> some View {
        switch tab {
        case .liveTrack:
            NavigationStack {
                LiveTrackView(vm: liveTrackVM)
                    .navigationTitle("Live Track")
                    .toolbar { settingsToolbarItem }
            }
        case .signal:
            NavigationStack {
                SignalView(vm: signalVM)
                    .navigationTitle("Signal Monitor")
            }
        case .chat:
            NavigationStack {
                ChatView(vm: chatVM)
                    .navigationTitle("AI Assistant")
                    .toolbar { resetChatToolbarItem }
            }
        case .planner:
            NavigationStack {
                PlannerView(vm: plannerVM)
                    .navigationTitle("Mission Planner")
            }
        case .alerts:
            NavigationStack {
                AlertsView(vm: alertsVM)
                    .navigationTitle("Anomaly Alerts")
                    .badge(alertsVM.unreadCount > 0 ? "\(alertsVM.unreadCount)" : nil)
            }
        }
    }

    // MARK: – Toolbar items

    private var settingsToolbarItem: some ToolbarContent {
        ToolbarItem(placement: .navigationBarTrailing) {
            NavigationLink {
                SettingsView()
                    .environmentObject(settings)
            } label: {
                Image(systemName: "gear")
            }
        }
    }

    private var resetChatToolbarItem: some ToolbarContent {
        ToolbarItem(placement: .navigationBarTrailing) {
            Button(role: .destructive) {
                Task { await chatVM.resetSession() }
            } label: {
                Image(systemName: "arrow.counterclockwise")
            }
        }
    }

    // MARK: – Dependency injection

    private func wireViewModels() {
        let url = settings.serverURL
        let nid = settings.noradID

        liveTrackVM.configure(serverURL: url, noradID: nid, locationService: locationService)
        signalVM.configure(locationService: locationService, signalService: signalService,
                           serverURL: url, noradID: nid)
        chatVM.configure(serverURL: url, noradID: nid)
        plannerVM.configure(serverURL: url, noradID: nid, locationService: locationService)
        alertsVM.configure(serverURL: url)
    }

    private func impactFeedback() {
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
    }
}

// MARK: – Settings sheet

struct SettingsView: View {
    @EnvironmentObject private var settings: AppSettings
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        Form {
            Section("Backend Server") {
                HStack {
                    Text("Host")
                    Spacer()
                    TextField("192.168.1.100", text: $settings.serverHost)
                        .multilineTextAlignment(.trailing)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                }
                HStack {
                    Text("Port")
                    Spacer()
                    TextField("5000", value: $settings.serverPort, format: .number)
                        .multilineTextAlignment(.trailing)
                        .keyboardType(.numberPad)
                }
            }
            Section("Satellite") {
                HStack {
                    Text("NORAD ID")
                    Spacer()
                    TextField("25544", text: $settings.noradID)
                        .multilineTextAlignment(.trailing)
                        .keyboardType(.numberPad)
                }
            }
            Section {
                HStack {
                    Text("App Version")
                    Spacer()
                    Text(AppConfig.appVersion).foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
    }
}
