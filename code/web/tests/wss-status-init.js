// Local transport fixture only. Deliberately does not provide OG/platform ready.
// This boot-only session connects to an actual local TLS WebSocket responder,
// not a Quake relay. No application or browser WebSocket implementation is mocked.
window.IOQ3_BOOT = Object.freeze({
    getSession: async () => ({
        endpoint: 'wss://localhost:4175',
        token: 'local-transport-fixture',
        sessionId: 'local-status-session',
        expiresAt: new Date(Date.now() + 60000).toISOString(),
        maxDatagramBytes: 16384,
        reconnectGraceMs: 15000,
    }),
});
