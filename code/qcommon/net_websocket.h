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
		sender: null, rtcCleanup: null, expiryTimer: null, deadlineTimer: null,
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
		clearTimeout(state.expiryTimer);
		clearTimeout(state.deadlineTimer);
		if (state.rtcCleanup) state.rtcCleanup();
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
	const expire = () => {
		if (Date.now() >= expires) { fail('session_expired'); return; }
		state.expiryTimer = setTimeout(expire, Math.min(expires - Date.now(), 2147483647));
	};
	expire();
	const reconnect = () => {
		if (state.reconnectSince !== null) return;
		state.reconnectSince = Date.now();
		state.deadlineTimer = setTimeout(() => fail('reconnect_expired'), 15000);
	};
	const ready = sender => {
		clearTimeout(state.authTimer);
		clearTimeout(state.deadlineTimer);
		state.sender = sender;
		state.ready = true;
		state.reconnectSince = null;
		state.retries = 0;
		try {
			for (const packet of state.outgoing) {
				if (sender.bufferedAmount + packet.byteLength <= 262144) sender.send(packet);
			}
		} catch (_) { state.sendFailed(); return; }
		state.outgoing.length = 0;
		state.outgoingBytes = 0;
		notify('ready', null);
	};
	const receive = (event, invalid) => {
		if (!state.ready || !(event.data instanceof ArrayBuffer) ||
			event.data.byteLength < 1 || event.data.byteLength > state.maxDatagramBytes) {
			invalid(); return;
		}
		if (state.incoming.length >= 128 || state.incomingBytes + event.data.byteLength > 1048576) return;
		state.incoming.push(new Uint8Array(event.data));
		state.incomingBytes += event.data.byteLength;
	};
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
		state.sendFailed = () => fail('send_failed');
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
				ready(socket);
				return;
			}
			receive(event, () => fail('invalid_datagram'));
		};
		socket.onerror = () => { /* close supplies the retry/terminal decision. */ };
		socket.onclose = event => {
			if (!current()) return;
			state.socket = null;
			state.sender = null;
			clearTimeout(state.authTimer);
			state.ready = false;
			state.outgoing.length = 0;
			state.outgoingBytes = 0;
			if (![1006, 1011, 1012, 1013].includes(event.code)) {
				fail('session_closed'); return;
			}
			reconnect();
			state.timer = setTimeout(connect, Math.min(250 * Math.pow(2, state.retries++), 2000));
		};
	};
	let rtcEndpoint;
	if (config.rtcEndpoint !== undefined) {
		try { rtcEndpoint = new URL(config.rtcEndpoint); }
		catch (_) { fail('invalid_session'); return; }
		if (rtcEndpoint.protocol !== 'wss:' || rtcEndpoint.username || rtcEndpoint.password ||
			rtcEndpoint.search || rtcEndpoint.hash) { fail('invalid_session'); return; }
	}
	const connectRTC = () => {
		if (state.stopped) return;
		let signaling, pc, dc, active = true, phase = 'config', opened = false;
		const current = () => active && !state.stopped;
		const cleanup = () => {
			active = false;
			clearTimeout(state.authTimer);
			state.ready = false;
			state.sender = null;
			if (dc) { dc.onopen = dc.onmessage = dc.onclose = dc.onerror = null; dc.close(); }
			if (pc) { pc.onicegatheringstatechange = pc.onconnectionstatechange = null; pc.close(); }
			if (signaling) {
				signaling.onopen = signaling.onmessage = signaling.onclose = signaling.onerror = null;
				signaling.close();
			}
			state.rtcCleanup = null;
		};
		const lost = () => {
			if (!current()) return;
			cleanup();
			state.incoming.length = state.outgoing.length = 0;
			state.incomingBytes = state.outgoingBytes = 0;
			reconnect();
			// A live RTC gets one fresh handshake. A failed handshake falls back
			// only after the signaling close handshake has actually finished.
			const closed = () => {
				if (signaling) signaling.onclose = null;
				if (state.stopped) return;
				if (opened) state.timer = setTimeout(connectRTC, 250);
				else connect();
			};
			if (!signaling || signaling.readyState === 3) closed();
			else signaling.onclose = closed;
		};
		state.rtcCleanup = cleanup;
		state.sendFailed = lost;
		notify(state.reconnectSince === null ? 'connecting' : 'reconnecting', null);
		state.authTimer = setTimeout(lost, 10000);
		try { signaling = new WebSocket(rtcEndpoint.href, 'og-rtc-v1'); }
		catch (_) { lost(); return; }
		signaling.onopen = () => {
			if (!current()) return;
			if (signaling.protocol !== 'og-rtc-v1') { lost(); return; }
			try { signaling.send(JSON.stringify({type: 'auth', token: token})); }
			catch (_) { lost(); }
		};
		signaling.onclose = signaling.onerror = lost;
		signaling.onmessage = async event => {
			if (!current()) return;
			try {
				if (typeof event.data !== 'string') throw new Error();
				const message = JSON.parse(event.data);
				if (phase === 'answer' && message.type === 'answer' && typeof message.sdp === 'string' && message.sdp) {
					phase = 'opening';
					await pc.setRemoteDescription({type: 'answer', sdp: message.sdp});
					return;
				}
				if (phase !== 'config' || message.type !== 'rtc-config' || message.sessionId !== sessionId ||
					message.maxDatagramBytes !== 16384 || !Array.isArray(message.iceServers)) throw new Error();
				phase = 'gathering';
				pc = new RTCPeerConnection({iceServers: message.iceServers});
				dc = pc.createDataChannel('og-udp-v1', {negotiated: true, id: 0, ordered: false, maxRetransmits: 0});
				dc.binaryType = 'arraybuffer';
				dc.onopen = () => {
					if (!current()) return;
					if (phase !== 'opening') { lost(); return; }
					phase = 'connected';
					opened = true;
					ready(dc);
				};
				dc.onmessage = event => { if (current()) receive(event, lost); };
				dc.onclose = dc.onerror = lost;
				pc.onconnectionstatechange = () => {
					if (['failed', 'disconnected', 'closed'].includes(pc.connectionState)) lost();
				};
				const offer = await pc.createOffer();
				if (!current()) return;
				await pc.setLocalDescription(offer);
				if (!current()) return;
				const gathered = () => {
					if (!current() || phase !== 'gathering' || pc.iceGatheringState !== 'complete') return;
					phase = 'answer';
					try { signaling.send(JSON.stringify({type: 'offer', sdp: pc.localDescription.sdp})); }
					catch (_) { lost(); }
				};
				pc.onicegatheringstatechange = gathered;
				gathered();
			} catch (_) { lost(); }
		};
	};
	if (rtcEndpoint && typeof RTCPeerConnection === 'function') connectRTC();
	else connect();
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
	if (state.ready && (state.sender.readyState === WebSocket.OPEN || state.sender.readyState === 'open')) {
		if (state.sender.bufferedAmount + length > 262144) return;
		try { state.sender.send(packet); }
		catch (_) { state.sendFailed(); }
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
