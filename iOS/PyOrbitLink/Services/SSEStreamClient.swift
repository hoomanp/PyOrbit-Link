import Foundation

// MARK: – SSE event parsed from raw text/event-stream data

struct RawSSEEvent {
    var eventType: String = "message"
    var data     : String = ""
}

// MARK: – Async SSE client using URLSession byte stream

actor SSEStreamClient: NSObject {

    private var dataTask: URLSessionDataTask?

    // MARK: – Public streaming entry point

    /// Returns an AsyncThrowingStream of SSETelemetryEvent
    func stream(path: String, query: [String: String] = [:], base: URL)
        -> AsyncThrowingStream<SSETelemetryEvent, Error>
    {
        AsyncThrowingStream { continuation in
            Task {
                await self.openStream(path: path, query: query, base: base,
                                       continuation: continuation)
            }
        }
    }

    // MARK: – Private stream opener

    private func openStream(
        path: String,
        query: [String: String],
        base: URL,
        continuation: AsyncThrowingStream<SSETelemetryEvent, Error>.Continuation
    ) async {
        var components = URLComponents(url: base.appendingPathComponent(path),
                                       resolvingAgainstBaseURL: false)!
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components.url else {
            continuation.finish(throwing: APIError.invalidURL)
            return
        }

        var request = URLRequest(url: url)
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.setValue("no-cache",          forHTTPHeaderField: "Cache-Control")
        request.timeoutInterval = AppConfig.sseTimeout

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest  = AppConfig.sseTimeout
        config.timeoutIntervalForResource = AppConfig.sseTimeout * 10
        let session = URLSession(configuration: config)

        do {
            let (bytes, response) = try await session.bytes(for: request)
            guard let http = response as? HTTPURLResponse,
                  (200..<300).contains(http.statusCode) else {
                continuation.finish(throwing: APIError.httpError(0, "Bad SSE response"))
                return
            }

            var currentEvent = RawSSEEvent()

            for try await line in bytes.lines {
                if line.isEmpty {
                    // Dispatch completed event
                    if let parsed = parse(event: currentEvent) {
                        continuation.yield(parsed)
                        if case .done = parsed.kind { break }
                    }
                    currentEvent = RawSSEEvent()
                } else if line.hasPrefix("event:") {
                    currentEvent.eventType = line.dropFirst(6).trimmingCharacters(in: .whitespaces)
                } else if line.hasPrefix("data:") {
                    let chunk = line.dropFirst(5).trimmingCharacters(in: .whitespaces)
                    currentEvent.data += (currentEvent.data.isEmpty ? "" : "\n") + chunk
                }
                // ignore comment lines starting with ":"
            }
            continuation.finish()
        } catch {
            continuation.finish(throwing: APIError.networkError(error))
        }
    }

    // MARK: – Event parser

    private func parse(event: RawSSEEvent) -> SSETelemetryEvent? {
        let data = event.data
        switch event.eventType {
        case "telemetry":
            guard let jsonData = data.data(using: .utf8),
                  let payload  = try? JSONDecoder().decode(TelemetryPayload.self, from: jsonData)
            else { return nil }
            return SSETelemetryEvent(kind: .telemetry(payload))

        case "token", "message":
            // Token may be raw JSON {"token":"..."} or bare string
            if let jsonData = data.data(using: .utf8),
               let obj  = try? JSONDecoder().decode([String: String].self, from: jsonData),
               let text = obj["token"] ?? obj["data"] {
                return SSETelemetryEvent(kind: .token(text))
            }
            return data.isEmpty ? nil : SSETelemetryEvent(kind: .token(data))

        case "done":
            return SSETelemetryEvent(kind: .done)

        case "error":
            return SSETelemetryEvent(kind: .error(data))

        default:
            // Try to decode as telemetry payload fallback
            if let jsonData = data.data(using: .utf8),
               let payload  = try? JSONDecoder().decode(TelemetryPayload.self, from: jsonData) {
                return SSETelemetryEvent(kind: .telemetry(payload))
            }
            return nil
        }
    }
}
