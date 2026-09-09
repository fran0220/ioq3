import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Exercise the actual EM_JS bodies, not a second implementation of the protocol.
const source = readFileSync(new URL('../../code/qcommon/net_websocket.h', import.meta.url), 'utf8');
const bodies = [...source.matchAll(/EM_JS\(\w+, (\w+), \(([^)]*)\), \{\n([\s\S]*?)\n\}\);/g)];
assert.equal(bodies.length, 4);

function harness(overrides = {}, rtc = {}) {
  let now = Date.parse('2026-09-09T00:00:00Z');
  let nextTimer = 0;
  const timers = new Map();
  const sockets = [];
  const statuses = [];
  const peers = [];
  const lifecycle = [];
  class Socket {
    static OPEN = 1;
    constructor(url, protocol) {
      lifecycle.push(`socket:${protocol}`);
      this.url = url;
      this.protocol = protocol;
      this.readyState = 0;
      this.bufferedAmount = 0;
      this.sent = [];
      sockets.push(this);
    }
    send(data) {
      assert.equal(this.readyState, 1);
      this.sent.push(typeof data === 'string' ? data : Array.from(data));
    }
    open() { this.readyState = 1; this.onopen?.(); }
    message(data) { this.onmessage?.({ data }); }
    ready(sessionId = 'session-a') { this.message(JSON.stringify({ type: 'ready', sessionId })); }
    close() { lifecycle.push('socket:close'); this.readyState = 3; this.onclose?.({ code: 1000 }); }
    disconnect(code = 1006) { this.readyState = 3; this.onclose?.({ code }); }
  }
  class Peer {
    constructor(config) {
      if (rtc.fail === 'constructor') throw new Error('RTC unavailable');
      this.config = config;
      this.iceGatheringState = 'gathering';
      peers.push(this);
    }
    createDataChannel(label, options) {
      if (rtc.fail === 'channel') throw new Error('channel failed');
      this.label = label; this.options = options;
      this.dc = {
        readyState: 'connecting', bufferedAmount: 0, sent: [],
        send(data) {
          assert.equal(this.readyState, 'open');
          if (rtc.fail === 'send') throw new Error('send failed');
          this.sent.push(Array.from(data)); this.bufferedAmount += data.byteLength;
        },
        close() { lifecycle.push('dc:close'); this.readyState = 'closed'; this.onclose?.(); },
        open() { this.readyState = 'open'; this.onopen?.(); },
        message(data) { this.onmessage?.({ data }); },
      };
      return this.dc;
    }
    async createOffer() {
      if (rtc.fail === 'offer') throw new Error('offer failed');
      if (rtc.offer) return rtc.offer;
      return { type: 'offer', sdp: 'initial-offer' };
    }
    async setLocalDescription(offer) {
      if (rtc.fail === 'local') throw new Error('local failed');
      this.localDescription = offer;
    }
    async setRemoteDescription(answer) {
      if (rtc.fail === 'answer') throw new Error('answer failed');
      this.remoteDescription = answer;
    }
    gather() {
      this.iceGatheringState = 'complete';
      this.localDescription = { type: 'offer', sdp: 'offer-with-final-candidates' };
      this.onicegatheringstatechange?.();
    }
    close() { lifecycle.push('pc:close'); this.connectionState = 'closed'; this.onconnectionstatechange?.(); }
  }
  const Module = {
    ogNetwork: {
      token: 'test-only-session-token', sessionId: 'session-a',
      endpoint: 'wss://native.example/v1/native/socket',
      expiresAt: '2026-09-09T01:00:00Z', maxDatagramBytes: 16384,
      reconnectGraceMs: 15000, ...overrides,
    },
    onNativeNetworkStatus: status => statuses.push(JSON.parse(JSON.stringify(status))),
  };
  const HEAPU8 = new Uint8Array(65536);
  const context = vm.createContext({
    Module, HEAPU8, WebSocket: Socket, URL, ArrayBuffer, Uint8Array,
    RTCPeerConnection: rtc.unavailable ? undefined : Peer,
    location: { hostname: 'game.example' },
    Date: { parse: Date.parse, now: () => now },
    setTimeout(fn, delay) { const id = ++nextTimer; timers.set(id, { fn, at: now + delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
  });
  for (const [, name, signature, body] of bodies) {
    const args = signature === 'void' ? '' : signature.split(',').map(arg => arg.trim().match(/\w+$/)[0]).join(',');
    vm.runInContext(`function ${name}(${args}) {\n${body}\n}`, context);
  }
  function advance(ms) {
    const until = now + ms;
    for (;;) {
      const entry = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
      if (!entry || entry[1].at > until) break;
      now = entry[1].at;
      timers.delete(entry[0]);
      entry[1].fn();
    }
    now = until;
  }
  return { Module, HEAPU8, sockets, statuses, timers, context, advance, peers, lifecycle };
}

test('auth precedes binary; queued packets copy WASM bytes and preserve message boundaries', () => {
  const h = harness();
  h.context.NET_WebStart();
  h.HEAPU8.set([255, 0, 19, 7], 3);
  h.context.NET_WebSend(3, 4);
  h.HEAPU8.fill(42);
  const socket = h.sockets[0];
  assert.equal(socket.url, 'wss://native.example/v1/native/socket');
  socket.open();
  assert.deepEqual(socket.sent.map(JSON.parse), [{ type: 'auth', token: 'test-only-session-token' }]);
  socket.ready();
  assert.deepEqual(socket.sent[1], [255, 0, 19, 7]);
  h.HEAPU8.set([1, 9], 20);
  h.context.NET_WebSend(20, 2);
  assert.deepEqual(socket.sent[2], [1, 9]);
  assert.deepEqual(h.statuses.at(-1), { state: 'ready', code: null });
});

test('receive yields one raw datagram at a time with no address header', () => {
  const h = harness();
  h.context.NET_WebStart();
  h.sockets[0].open(); h.sockets[0].ready();
  h.sockets[0].message(Uint8Array.from([255, 255, 255, 255, 1, 0, 83]).buffer);
  h.sockets[0].message(Uint8Array.from([17, 23]).buffer);
  assert.equal(h.context.NET_WebReceive(13, 16385), 7);
  assert.deepEqual(Array.from(h.HEAPU8.slice(13, 20)), [255, 255, 255, 255, 1, 0, 83]);
  assert.equal(h.context.NET_WebReceive(13, 16385), 2);
  assert.deepEqual(Array.from(h.HEAPU8.slice(13, 15)), [17, 23]);
  assert.equal(h.context.NET_WebReceive(13, 16385), 0);
});

test('session identity and binary-before-ready are enforced', () => {
  for (const message of [JSON.stringify({ type: 'ready', sessionId: 'other' }), new ArrayBuffer(3), 'null']) {
    const h = harness(); h.context.NET_WebStart(); h.sockets[0].open();
    h.sockets[0].message(message);
    assert.equal(h.Module.__ioq3Network.stopped, true);
    assert.equal(h.statuses.at(-1).state, 'failed');
    assert.equal(h.timers.size, 0);
  }
});

test('oversized datagrams fail, exact protocol maximum succeeds', () => {
  const h = harness(); h.context.NET_WebStart(); h.sockets[0].open(); h.sockets[0].ready();
  h.sockets[0].message(new ArrayBuffer(16384));
  assert.equal(h.context.NET_WebReceive(0, 16385), 16384);
  h.sockets[0].message(new ArrayBuffer(16385));
  assert.equal(h.statuses.at(-1).code, 'invalid_datagram');
});

test('a too-small receive buffer drops that packet without losing the following valid packet', () => {
  const h = harness(); h.context.NET_WebStart(); h.sockets[0].open(); h.sockets[0].ready();
  h.sockets[0].message(new ArrayBuffer(8));
  h.sockets[0].message(Uint8Array.from([91, 4, 2]).buffer);
  assert.equal(h.context.NET_WebReceive(0, 8), 3);
  assert.deepEqual(Array.from(h.HEAPU8.slice(0, 3)), [91, 4, 2]);
  assert.equal(h.Module.__ioq3Network.incomingBytes, 0);
});

test('incoming, pre-auth outgoing and socket backpressure are bounded', () => {
  const h = harness(); h.context.NET_WebStart();
  for (let i = 0; i < 70; i++) h.context.NET_WebSend(0, 3);
  assert.equal(h.Module.__ioq3Network.outgoing.length, 64);
  h.sockets[0].open(); h.sockets[0].ready();
  for (let i = 0; i < 150; i++) h.sockets[0].message(new ArrayBuffer(5));
  assert.equal(h.Module.__ioq3Network.incoming.length, 128);
  h.sockets[0].bufferedAmount = 262143;
  h.context.NET_WebSend(0, 2);
  assert.equal(h.sockets[0].sent.length, 65);
  for (let i = 0; i < 128; i++) h.context.NET_WebReceive(0, 8);
  for (let i = 0; i < 70; i++) h.sockets[0].message(new ArrayBuffer(16384));
  assert.equal(h.Module.__ioq3Network.incomingBytes, 1048576);
});

test('transient disconnect reauthenticates same token without replaying sent datagrams', () => {
  const h = harness(); h.context.NET_WebStart(); h.sockets[0].open(); h.sockets[0].ready();
  h.context.NET_WebSend(0, 5);
  const oldMessage = h.sockets[0].onmessage;
  h.sockets[0].disconnect();
  h.advance(249); assert.equal(h.sockets.length, 1);
  h.advance(1); assert.equal(h.sockets.length, 2);
  oldMessage({ data: new ArrayBuffer(9) });
  assert.equal(h.Module.__ioq3Network.incoming.length, 0);
  h.sockets[1].open(); h.sockets[1].ready();
  assert.equal(h.sockets[1].sent.length, 1);
  assert.equal(JSON.parse(h.sockets[1].sent[0]).token, 'test-only-session-token');
});

test('terminal close and net stop do not reconnect; restart isolates stale callbacks', () => {
  const h = harness(); h.context.NET_WebStart(); h.sockets[0].open();
  h.sockets[0].disconnect(1008); h.advance(20000);
  assert.equal(h.sockets.length, 1);
  assert.equal(h.statuses.at(-1).code, 'session_closed');
  h.context.NET_WebStart();
  const oldReady = h.sockets[1].onmessage;
  h.context.NET_WebStop(); h.advance(20000);
  assert.equal(h.Module.__ioq3Network, undefined);
  h.context.NET_WebStart(); oldReady({ data: JSON.stringify({ type: 'ready', sessionId: 'session-a' }) });
  assert.equal(h.Module.__ioq3Network.ready, false);
});

test('retry window is bounded and expired sessions are never reopened', () => {
  const h = harness(); h.context.NET_WebStart(); h.sockets[0].open(); h.sockets[0].ready();
  h.sockets[0].disconnect();
  for (let i = 0; i < 20 && !h.Module.__ioq3Network.stopped; i++) {
    h.advance(2000);
    h.sockets.at(-1).disconnect();
  }
  assert.equal(h.statuses.at(-1).code, 'reconnect_expired');
  const expired = harness({ expiresAt: '2026-09-09T00:00:00Z' });
  expired.context.NET_WebStart();
  assert.equal(expired.sockets.length, 0);
});

test('unsafe endpoint or invalid contract is rejected without disclosing token', () => {
  for (const override of [
    { endpoint: 'ws://native.example/v1/native/socket' },
    { endpoint: 'wss://name:secret@native.example/v1/native/socket' },
    { endpoint: 'wss://native.example/v1/native/socket?token=secret' },
    { maxDatagramBytes: 65536 }, { reconnectGraceMs: 600000 }, { sessionId: '' },
  ]) {
    const h = harness(override); h.context.NET_WebStart();
    assert.equal(h.sockets.length, 0);
    assert.deepEqual(h.statuses, [{ state: 'failed', code: 'invalid_session' }]);
    assert.ok(!JSON.stringify(h.statuses).includes(h.Module.ogNetwork.token));
  }
});

test('missing session, bad subprotocol and stalled handshake fail explicitly', () => {
  const h = harness(); h.Module.ogNetwork = null; h.context.NET_WebStart();
  assert.equal(h.statuses.at(-1).code, 'session_missing');
  const bad = harness(); bad.context.NET_WebStart(); bad.sockets[0].protocol = ''; bad.sockets[0].open();
  assert.equal(bad.statuses.at(-1).code, 'protocol_mismatch');
  const stalled = harness(); stalled.context.NET_WebStart(); stalled.advance(10000);
  assert.equal(stalled.statuses.at(-1).code, 'handshake_timeout');
});

const rtcEndpoint = 'wss://native.example/v1/native/rtc';
const iceServers = [{ urls: ['turn:relay.example:3478'], username: 'ephemeral', credential: 'test-only' }];
async function configureRTC(h) {
  const ws = h.sockets.at(-1);
  ws.open();
  await ws.onmessage({ data: JSON.stringify({ type: 'rtc-config', sessionId: 'session-a', maxDatagramBytes: 16384, iceServers }) });
  return h.peers.at(-1);
}
async function openRTC(h) {
  const pc = await configureRTC(h);
  pc.gather();
  await h.sockets.at(-1).onmessage({ data: JSON.stringify({ type: 'answer', sdp: 'server-answer' }) });
  pc.dc.open();
  return pc;
}

test('RTC negotiates exact channel and server ICE config, waits for full ICE and DC open', async () => {
  const h = harness({ rtcEndpoint }); h.context.NET_WebStart();
  h.HEAPU8.set([91, 0, 255], 7); h.context.NET_WebSend(7, 3); h.HEAPU8.fill(42);
  const pc = await configureRTC(h);
  assert.equal(h.sockets[0].protocol, 'og-rtc-v1');
  assert.deepEqual(JSON.parse(h.sockets[0].sent[0]), { type: 'auth', token: 'test-only-session-token' });
  assert.deepEqual(JSON.parse(JSON.stringify(pc.config)), { iceServers });
  assert.equal(pc.label, 'og-udp-v1');
  assert.deepEqual(JSON.parse(JSON.stringify(pc.options)), { negotiated: true, id: 0, ordered: false, maxRetransmits: 0 });
  assert.equal(pc.dc.binaryType, 'arraybuffer');
  assert.equal(h.sockets[0].sent.length, 1);
  pc.gather(); pc.gather();
  assert.deepEqual(JSON.parse(h.sockets[0].sent[1]), { type: 'offer', sdp: 'offer-with-final-candidates' });
  assert.equal(h.sockets[0].sent.length, 2);
  await h.sockets[0].onmessage({ data: JSON.stringify({ type: 'answer', sdp: 'server-answer' }) });
  assert.equal(h.Module.__ioq3Network.ready, false);
  assert.equal(pc.dc.sent.length, 0);
  pc.dc.open();
  assert.deepEqual(pc.dc.sent, [[91, 0, 255]]);
  assert.equal(h.sockets[0].readyState, 1, 'signaling remains open');
  assert.equal(h.sockets.length, 1, 'no parallel WSS transport');
});

test('RTC queues, backpressure, message boundaries and maximum datagram apply to raw binary', async () => {
  const h = harness({ rtcEndpoint }); h.context.NET_WebStart();
  for (let i = 0; i < 70; i++) h.context.NET_WebSend(0, 16384);
  assert.equal(h.Module.__ioq3Network.outgoingBytes, 262144);
  const pc = await configureRTC(h); pc.gather();
  await h.sockets[0].onmessage({ data: JSON.stringify({ type: 'answer', sdp: 'answer' }) });
  pc.dc.bufferedAmount = 262144 - 16384; pc.dc.open();
  assert.equal(pc.dc.sent.length, 1, 'flush also respects backpressure');
  h.context.NET_WebSend(0, 1); assert.equal(pc.dc.sent.length, 1);
  pc.dc.bufferedAmount = 262144 - 16384;
  h.context.NET_WebSend(0, 16385); h.context.NET_WebSend(0, 0);
  h.context.NET_WebSend(0, 16384); assert.equal(pc.dc.sent.length, 2);
  pc.dc.message(new ArrayBuffer(16384));
  pc.dc.message(Uint8Array.from([71, 0, 13]).buffer);
  assert.equal(h.context.NET_WebReceive(0, 16385), 16384);
  assert.equal(h.context.NET_WebReceive(0, 16385), 3);
  assert.deepEqual(Array.from(h.HEAPU8.slice(0, 3)), [71, 0, 13]);
  for (let i = 0; i < 140; i++) pc.dc.message(new ArrayBuffer(3));
  assert.equal(h.Module.__ioq3Network.incoming.length, 128);
  for (let i = 0; i < 128; i++) h.context.NET_WebReceive(0, 4);
  for (let i = 0; i < 70; i++) pc.dc.message(new ArrayBuffer(16384));
  assert.equal(h.Module.__ioq3Network.incomingBytes, 1048576);
});

test('RTC negotiation exceptions clean resources before WSS construction', async () => {
  for (const fail of ['constructor', 'channel', 'offer', 'local', 'answer']) {
    const h = harness({ rtcEndpoint }, { fail }); h.context.NET_WebStart();
    const pc = await configureRTC(h);
    if (fail === 'answer') {
      pc.gather();
      await h.sockets[0].onmessage({ data: JSON.stringify({ type: 'answer', sdp: 'bad-answer' }) });
    }
    assert.equal(h.sockets.length, 2, fail);
    assert.equal(h.sockets[1].protocol, 'og-udp-v1');
    const end = h.lifecycle.indexOf('socket:og-udp-v1');
    assert.ok(h.lifecycle.indexOf('socket:close') < end);
    if (pc) assert.ok(h.lifecycle.indexOf('pc:close') < end);
    if (pc?.dc) assert.ok(h.lifecycle.indexOf('dc:close') < end);
  }
});

test('RTC stalls in config, ICE, answer or channel-open fall back after 10 seconds', async () => {
  for (const phase of ['config', 'ice', 'answer', 'open']) {
    const h = harness({ rtcEndpoint }); h.context.NET_WebStart();
    if (phase !== 'config') {
      const pc = await configureRTC(h);
      if (phase !== 'ice') pc.gather();
      if (phase === 'open') await h.sockets[0].onmessage({ data: JSON.stringify({ type: 'answer', sdp: 'answer' }) });
    }
    h.advance(9999); assert.equal(h.sockets.length, 1);
    h.advance(1); assert.equal(h.sockets.length, 2);
    assert.equal(h.sockets[0].readyState, 3);
    assert.equal(h.sockets[1].protocol, 'og-udp-v1');
  }
});

test('RTC live disconnect reauthenticates a fresh PC; failed rehandshake falls back inside original deadline', async () => {
  const h = harness({ rtcEndpoint }); h.context.NET_WebStart();
  const pc = await openRTC(h);
  const oldOpen = pc.dc.onopen, oldMessage = pc.dc.onmessage;
  pc.dc.close();
  h.advance(249); assert.equal(h.sockets.length, 1);
  h.advance(1); const next = await configureRTC(h);
  assert.notEqual(next, pc);
  assert.equal(JSON.parse(h.sockets[1].sent[0]).token, 'test-only-session-token');
  oldOpen(); oldMessage({ data: new ArrayBuffer(4) });
  assert.equal(h.Module.__ioq3Network.ready, false);
  assert.equal(h.Module.__ioq3Network.incoming.length, 0);
  h.advance(10000); assert.equal(h.sockets[2].protocol, 'og-udp-v1');
  h.advance(4749); assert.equal(h.Module.__ioq3Network.stopped, false);
  h.advance(1); assert.equal(h.statuses.at(-1).code, 'reconnect_expired');
  assert.equal(h.timers.size, 0);
});

test('successful RTC reconnect cancels the old 15-second deadline', async () => {
  const h = harness({ rtcEndpoint }); h.context.NET_WebStart();
  const pc = await openRTC(h); pc.connectionState = 'failed'; pc.onconnectionstatechange();
  h.advance(250); const next = await openRTC(h);
  h.advance(15000);
  assert.equal(h.Module.__ioq3Network.ready, true);
  assert.equal(next.dc.readyState, 'open');
});

test('RTC expiry and stop close signaling, peer and channel without fallback', async () => {
  for (const stop of [false, true]) {
    const h = harness({ rtcEndpoint, expiresAt: '2026-09-09T00:00:05Z' }); h.context.NET_WebStart();
    const pc = await openRTC(h);
    if (stop) h.context.NET_WebStop(); else h.advance(5000);
    assert.equal(pc.dc.readyState, 'closed'); assert.equal(pc.connectionState, 'closed');
    assert.equal(h.sockets[0].readyState, 3); assert.equal(h.timers.size, 0);
    h.advance(20000); assert.equal(h.sockets.length, 1);
    if (!stop) assert.equal(h.statuses.at(-1).code, 'session_expired');
  }
});

test('pending RTC async offer completion after restart cannot touch a new session', async () => {
  let resolve;
  const h = harness({ rtcEndpoint }, { offer: new Promise(r => { resolve = r; }) });
  h.context.NET_WebStart(); const pending = configureRTC(h);
  const old = h.peers[0];
  h.context.NET_WebStart();
  resolve({ type: 'offer', sdp: 'stale' }); await pending;
  assert.equal(old.localDescription, undefined);
  assert.equal(h.sockets[0].sent.length, 1);
  assert.equal(h.sockets.length, 2);
  assert.equal(h.Module.__ioq3Network.ready, false);
});

test('RTC malformed config, binary signaling and invalid data never become ready', async () => {
  for (const data of ['null', '{}', new ArrayBuffer(4), JSON.stringify({ type: 'rtc-config', sessionId: 'wrong', maxDatagramBytes: 16384, iceServers })]) {
    const h = harness({ rtcEndpoint }); h.context.NET_WebStart(); h.sockets[0].open();
    await h.sockets[0].onmessage({ data });
    assert.equal(h.sockets.at(-1).protocol, 'og-udp-v1');
    assert.equal(h.Module.__ioq3Network.ready, false);
  }
  for (const data of [new ArrayBuffer(0), new ArrayBuffer(16385), 'text']) {
    const h = harness({ rtcEndpoint }); h.context.NET_WebStart(); const pc = await openRTC(h);
    pc.dc.message(data);
    assert.equal(pc.connectionState, 'closed');
    assert.equal(h.Module.__ioq3Network.incoming.length, 0);
  }
});

test('optional RTC absence or unavailable browser retains WSS; unsafe RTC URL fails closed', () => {
  const h = harness({ rtcEndpoint }, { unavailable: true }); h.context.NET_WebStart();
  assert.equal(h.sockets[0].protocol, 'og-udp-v1');
  for (const url of ['ws://native.example/rtc', `${rtcEndpoint}?token=secret`, 'wss://user:pass@native.example/rtc', `${rtcEndpoint}#secret`]) {
    const bad = harness({ rtcEndpoint: url }); bad.context.NET_WebStart();
    assert.equal(bad.sockets.length, 0); assert.equal(bad.timers.size, 0);
    assert.equal(bad.statuses.at(-1).code, 'invalid_session');
  }
});

test('RTC fallback waits for actual signaling CLOSED, not just close() invocation', async () => {
  for (const stop of [false, true]) {
    const h = harness({ rtcEndpoint }); h.context.NET_WebStart();
    const pc = await configureRTC(h), ws = h.sockets[0];
    ws.close = () => { ws.readyState = 2; };
    pc.dc.onerror();
    assert.equal(pc.connectionState, 'closed');
    assert.equal(pc.dc.readyState, 'closed');
    h.advance(1000); assert.equal(h.sockets.length, 1);
    const closed = ws.onclose;
    if (stop) h.context.NET_WebStop();
    ws.readyState = 3; closed();
    assert.equal(h.sockets.length, stop ? 1 : 2);
    if (!stop) assert.equal(h.sockets[1].protocol, 'og-udp-v1');
  }
});

test('RTC signaling close stalls terminate at deadline without racing a fallback', async () => {
  const h = harness({ rtcEndpoint }); h.context.NET_WebStart();
  const pc = await configureRTC(h), ws = h.sockets[0];
  ws.close = () => { ws.readyState = 2; };
  pc.dc.onerror(); h.advance(15000);
  assert.equal(h.statuses.at(-1).code, 'reconnect_expired');
  assert.equal(h.sockets.length, 1);
});

test('RTC send failure cleans a live connection and never replays failed bytes', async () => {
  const rtc = {};
  const h = harness({ rtcEndpoint }, rtc); h.context.NET_WebStart();
  const pc = await openRTC(h); rtc.fail = 'send';
  h.context.NET_WebSend(0, 7);
  assert.equal(pc.connectionState, 'closed');
  assert.equal(h.Module.__ioq3Network.outgoing.length, 0);
  rtc.fail = undefined; h.advance(250); const next = await openRTC(h);
  assert.equal(next.dc.sent.length, 0);
});
