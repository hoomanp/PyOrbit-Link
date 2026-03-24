import Foundation

// MARK: – Errors

enum APIError: LocalizedError {
    case invalidURL
    case httpError(Int, String?)
    case decodingError(Error)
    case networkError(Error)
    case noData

    var errorDescription: String? {
        switch self {
        case .invalidURL:           return "Invalid server URL."
        case .httpError(let c, let m): return "HTTP \(c): \(m ?? "unknown")"
        case .decodingError(let e): return "Decode failed: \(e.localizedDescription)"
        case .networkError(let e):  return e.localizedDescription
        case .noData:               return "Empty response."
        }
    }
}

// MARK: – REST client

actor APIClient {

    private let session: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest  = 15
        config.timeoutIntervalForResource = 30
        session = URLSession(configuration: config)
    }

    // MARK: – GET

    func get<T: Decodable>(_ path: String, base: URL) async throws -> T {
        let url  = base.appendingPathComponent(path)
        var req  = URLRequest(url: url)
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        return try await execute(req)
    }

    func getWithQuery<T: Decodable>(_ path: String, query: [String: String], base: URL) async throws -> T {
        var components = URLComponents(url: base.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        guard let url = components.url else { throw APIError.invalidURL }
        var req = URLRequest(url: url)
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        return try await execute(req)
    }

    // MARK: – POST

    func post<B: Encodable, T: Decodable>(_ path: String, body: B, base: URL) async throws -> T {
        let url  = base.appendingPathComponent(path)
        var req  = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.httpBody   = try JSONEncoder().encode(body)
        return try await execute(req)
    }

    func postEmpty<T: Decodable>(_ path: String, base: URL) async throws -> T {
        let url  = base.appendingPathComponent(path)
        var req  = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        return try await execute(req)
    }

    // MARK: – Fetch alerts

    func fetchAlerts(base: URL) async throws -> [AnomalyAlert] {
        try await get("/api/alerts", base: base)
    }

    // MARK: – Plan

    func plan(message: String, base: URL) async throws -> PlanResult {
        struct Body: Encodable { let message: String }
        return try await post("/api/plan", body: Body(message: message), base: base)
    }

    // MARK: – Chat

    func chat(message: String, base: URL) async throws -> ChatResponse {
        try await post("/api/chat", body: ChatRequest(message: message), base: base)
    }

    func resetChat(base: URL) async throws -> ChatResetResponse {
        try await postEmpty("/api/chat/reset", base: base)
    }

    // MARK: – Private executor

    private func execute<T: Decodable>(_ request: URLRequest) async throws -> T {
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else { throw APIError.noData }
            guard (200..<300).contains(http.statusCode) else {
                let msg = String(data: data, encoding: .utf8)
                throw APIError.httpError(http.statusCode, msg)
            }
            do {
                return try JSONDecoder().decode(T.self, from: data)
            } catch {
                throw APIError.decodingError(error)
            }
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.networkError(error)
        }
    }
}
