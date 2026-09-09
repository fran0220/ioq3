/*
 * Origin Game's room-bound datagram transport for the Emscripten client.
 * SPDX-License-Identifier: GPL-2.0-or-later
 * Included only by net_ip.c; native UDP and the Quake netchan stay unchanged.
 */
#include <emscripten.h>

EM_JS(void, NET_WebStart, (void), {
	const previous = Module.__ioq3Network;
	if (previous) previous.stop();
	const state = {
		socket: null, stopped: false, ready: false, timer: null,
		authTimer: null, reconnectSince: null, incoming: [], outgoing: [],
		incomingBytes: 0, outgoingBytes: 0, retries: 0
	};
	Module.__ioq3Network = state;
	const notify = (status, code) => {
		if (typeof Module.onNativeNetworkStatus === 'function') {
			try { Module.onNativeNetworkStatus({state: status, code: code}); }
			catch (_) { /* A host UI callback must not break the transport. */ }
		}
	};
	state.stop = () => {
		state.stopped = true;
		state.ready = false;
		clearTimeout(state.timer);
		clearTimeout(state.authTimer);
		state.incoming.length = state.outgoing.length = 0;
		state.incomingBytes = state.outgoingBytes = 0;
		if (state.socket) {
			state.socket.onopen = state.socket.onmessage = null;
			state.socket.onclose = state.socket.onerror = null;
			state.socket.close();
		}
	};
	const fail = code => { state.stop(); notify('failed', code); };
	const config = Module.ogNetwork;
	if (!config) { fail('session_missing'); return; }
	const token = config.token;
	const sessionId = config.sessionId;
	const expires = Date.parse(config.expiresAt);
	let endpoint;
	try { endpoint = new URL(config.endpoint); }
	catch (_) { fail('invalid_session'); return; }
	const local = typeof location !== 'undefined' &&
		['localhost', '127.0.0.1', '[::1]'].includes(location.hostname) &&
		['localhost', '127.0.0.1', '[::1]'].includes(endpoint.hostname);
	if ((endpoint.protocol !== 'wss:' && !(local && endpoint.protocol === 'ws:')) ||
		endpoint.username || endpoint.password || endpoint.search || endpoint.hash ||
		typeof token !== 'string' || !token || typeof sessionId !== 'string' || !sessionId ||
		!Number.isFinite(expires) || expires <= Date.now() ||
		config.maxDatagramBytes !== 16384 || config.reconnectGraceMs !== 15000) {
		fail('invalid_session'); return;
	}
	state.maxDatagramBytes = config.maxDatagramBytes;
	state.fail = fail;
	const connect = () => {
		if (state.stopped) return;
		if (Date.now() >= expires) { fail('session_expired'); return; }
		if (state.reconnectSince !== null && Date.now() - state.reconnectSince >= 15000) {
			fail('reconnect_expired'); return;
		}
		notify(state.reconnectSince === null ? 'connecting' : 'reconnecting', null);
		let socket;
		try { socket = new WebSocket(endpoint.href, 'og-udp-v1'); }
		catch (_) { fail('socket_unavailable'); return; }
		state.socket = socket;
		socket.binaryType = 'arraybuffer';
		const current = () => !state.stopped && state.socket === socket;
		state.authTimer = setTimeout(() => {
			if (current() && !state.ready) fail('handshake_timeout');
		}, 10000);
		socket.onopen = () => {
			if (!current()) return;
			if (socket.protocol !== 'og-udp-v1') { fail('protocol_mismatch'); return; }
			try { socket.send(JSON.stringify({type: 'auth', token: token})); }
			catch (_) { fail('authentication_send_failed'); }
		};
		socket.onmessage = event => {
			if (!current()) return;
			if (typeof event.data === 'string') {
				let message;
				try { message = JSON.parse(event.data); }
				catch (_) { fail('invalid_control_message'); return; }
				if (!message || message.type !== 'ready' || message.sessionId !== sessionId || state.ready) {
					fail('invalid_control_message'); return;
				}
				clearTimeout(state.authTimer);
				state.ready = true;
				state.reconnectSince = null;
				state.retries = 0;
				try {
					for (const packet of state.outgoing) socket.send(packet);
				} catch (_) { fail('send_failed'); return; }
				state.outgoing.length = 0;
				state.outgoingBytes = 0;
				notify('ready', null);
				return;
			}
			if (!state.ready || !(event.data instanceof ArrayBuffer) ||
				event.data.byteLength < 1 || event.data.byteLength > state.maxDatagramBytes) {
				fail('invalid_datagram'); return;
			}
			// Drop overflow like UDP rather than grow unbounded or block the frame.
			if (state.incoming.length >= 128 || state.incomingBytes + event.data.byteLength > 1048576) return;
			state.incoming.push(new Uint8Array(event.data));
			state.incomingBytes += event.data.byteLength;
		};
		socket.onerror = () => { /* close supplies the retry/terminal decision. */ };
		socket.onclose = event => {
			if (!current()) return;
			clearTimeout(state.authTimer);
			state.ready = false;
			state.outgoing.length = 0;
			state.outgoingBytes = 0;
			if (![1006, 1011, 1012, 1013].includes(event.code)) {
				fail('session_closed'); return;
			}
			if (state.reconnectSince === null) state.reconnectSince = Date.now();
			state.timer = setTimeout(connect, Math.min(250 * Math.pow(2, state.retries++), 2000));
		};
	};
	connect();
});

EM_JS(void, NET_WebStop, (void), {
	if (Module.__ioq3Network) Module.__ioq3Network.stop();
	delete Module.__ioq3Network;
});

EM_JS(void, NET_WebSend, (const void *data, int length), {
	const state = Module.__ioq3Network;
	if (!state || state.stopped || length < 1 || length > state.maxDatagramBytes) return;
	// Copy before returning to C: its packet buffer may be immediately reused.
	const packet = HEAPU8.slice(data, data + length);
	if (state.ready && state.socket.readyState === WebSocket.OPEN) {
		if (state.socket.bufferedAmount + length > 262144) return;
		try { state.socket.send(packet); }
		catch (_) { state.fail('send_failed'); }
	} else if (state.outgoing.length < 64 && state.outgoingBytes + length <= 262144) {
		state.outgoing.push(packet);
		state.outgoingBytes += length;
	}
});

EM_JS(int, NET_WebReceive, (void *data, int capacity), {
	const state = Module.__ioq3Network;
	if (!state || state.stopped) return 0;
	while (state.incoming.length) {
		const packet = state.incoming.shift();
		state.incomingBytes -= packet.byteLength;
		if (packet.byteLength >= capacity) continue;
		HEAPU8.set(packet, data);
		return packet.byteLength;
	}
	return 0;
});
