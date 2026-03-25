import SwiftUI

@main
struct ConstellaSimApp: App {

    @StateObject private var locationService   = LocationService()
    @StateObject private var signalService     = SignalMonitorService()
    @StateObject private var appSettings       = AppSettings()

    init() {
        configureAppearance()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(locationService)
                .environmentObject(signalService)
                .environmentObject(appSettings)
                .task { await locationService.requestPermission() }
                .task { signalService.start() }
        }
    }

    // MARK: – Global appearance

    private func configureAppearance() {
        let navAppearance = UINavigationBarAppearance()
        navAppearance.configureWithOpaqueBackground()
        navAppearance.backgroundColor = UIColor(named: "AccentBackground") ?? .systemBackground
        navAppearance.titleTextAttributes = [.foregroundColor: UIColor.label]
        UINavigationBar.appearance().standardAppearance  = navAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navAppearance

        let tabAppearance = UITabBarAppearance()
        tabAppearance.configureWithOpaqueBackground()
        UITabBar.appearance().standardAppearance  = tabAppearance
        UITabBar.appearance().scrollEdgeAppearance = tabAppearance
    }
}

// MARK: – App-wide user settings (persisted)

final class AppSettings: ObservableObject {
    @Published var serverHost: String {
        didSet { UserDefaults.standard.set(serverHost, forKey: "serverHost") }
    }
    @Published var serverPort: Int {
        didSet { UserDefaults.standard.set(serverPort, forKey: "serverPort") }
    }
    @Published var noradID: String {
        didSet { UserDefaults.standard.set(noradID, forKey: "noradID") }
    }

    var serverURL: URL {
        URL(string: "http://\(serverHost):\(serverPort)")!
    }

    init() {
        serverHost = UserDefaults.standard.string(forKey: "serverHost") ?? AppConfig.defaultHost
        serverPort = UserDefaults.standard.integer(forKey: "serverPort").nonZero ?? AppConfig.defaultPort
        noradID    = UserDefaults.standard.string(forKey: "noradID")   ?? AppConfig.defaultNoradID
    }
}

private extension Int {
    var nonZero: Int? { self == 0 ? nil : self }
}
