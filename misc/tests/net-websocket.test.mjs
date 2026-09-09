import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Exercise the actual EM_JS bodies, not a second implementation of the protocol.
const source = readFileSync(new URL('../../code/qcommon/net_websocket.h', import.meta.url), 'utf8');
const bodies = [...source.matchAll(/EM_JS\(\w+, (\w+), \(([^)]*)\), \{\n([\s\S]*?)\n\}\);/g)];
assert.equal(bodies.length, 4);

function harness(overrides = {}) {
  let now = Date.parse('2026-09-09T00:00:00Z');
  let nextTimer = 0;
  const timers = new Map();
  const sockets = [];
  const statuses = [];
  class Socket {
    static OPEN = 1;
    constructor(url, protocol) {
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
    close() { this.readyState = 3; this.onclose?.({ code: 1000 }); }
    disconnect(code = 1006) { this.readyState = 3; this.onclose?.({ code }); }
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
  return { Module, HEAPU8, sockets, statuses, timers, context, advance };
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
