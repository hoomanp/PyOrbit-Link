import Foundation

enum AppConfig {

    // MARK: – Backend defaults (override in Settings tab)
    static let defaultHost    = "192.168.1.100"   // LAN IP of the Flask server
    static let defaultPort    = 5000
    static let defaultNoradID = "25544"            // ISS

    // MARK: – SSE / streaming
    static let sseTimeout: TimeInterval       = 90
    static let streamChunkBufferSize          = 4096

    // MARK: – Chat
    static let maxChatTurns = 10

    // MARK: – Signal history window
    static let signalHistorySeconds = 120   // 2 min rolling window @ 1 Hz
    static let aerHistorySeconds    = 60

    // MARK: – Anomaly polling
    static let alertPollInterval: TimeInterval = 5

    // MARK: – App Store metadata
    static let bundleID     = "com.pyorbitlink.app"
    static let appVersion   = "1.0.0"
    static let buildNumber  = "1"
    static let teamID       = "XXXXXXXXXX"   // Replace with your Apple Developer Team ID

    // MARK: – Physics constants used in UI
    static let speedOfLight: Double = 299_792_458   // m/s
    static let frequencyHz: Double  = 437_525_000   // 437.525 MHz (UHF amateur)

    // MARK: – Convenience URL (used as default in ViewModels)
    static let defaultServerURL = URL(string: "http://\(defaultHost):\(defaultPort)")!
}
