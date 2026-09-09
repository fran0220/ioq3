# PC Web native multiplayer integration

The Web client retains Quake's challenge/connect and netchan packet contents.
`code/qcommon/net_websocket.h` implements the Origin Game `og-udp-v1` transport;
`net_ip.c` switches only the Emscripten socket boundary. Native builds retain UDP.

## Session contract

The trusted room service selects the dedicated server. A browser creates a session
by POSTing `{}` to `/v1/native/rooms/:roomId/sessions` with a short-lived room join
capability in `Authorization: Bearer …`. The service validates the exact Origin.
The native service response is passed in memory as `Module.ogNetwork`:

```js
{
  sessionId, token, endpoint, expiresAt,
  maxDatagramBytes: 16384,
  reconnectGraceMs: 15000
}
```

`expiresAt` is an ISO timestamp. `endpoint` is a WSS URL with no credentials,
query or fragment. WS is allowed only between localhost pages and localhost
endpoints for development. These credentials must not be archived in cvars,
manifests, browser storage, URLs or logs. The service management key never reaches
the browser. The creator identity for game publication remains `og-atlas`,
independent of room/session capabilities.

After WebSocket OPEN with subprotocol `og-udp-v1`, the client sends a text auth
message `{type:'auth',token}`. Only after receiving `{type:'ready',sessionId}` does
it send binary messages. Each binary message in either direction is one raw UDP
datagram, without an address/length prefix. The browser cannot select UDP targets.

`connect origingame` uses the fixed logical peer `192.0.2.1:27960` inside the
engine. That reserved documentation address is not an Internet server or a
portal: packets go through the authenticated room connection. IPv6, LAN discovery
and arbitrary server/master DNS are not supported by this browser transport.
Local engine loopback for offline Bot play remains separate.

The host enables `net_enabled 1` only with a valid session; absent configuration
keeps networking disabled. `net_restart` tears down the previous socket and reads
the current in-memory session. A short transient disconnect retries the same
token within the 15-second grace period, preserving the server-side UDP source
port if the service accepts it. Already-sent datagrams are never replayed by the
transport. Expired/revoked sessions require a new POST and Quake challenge/connect.

`Module.onNativeNetworkStatus({state,code})` receives credential-free status:
connecting, reconnecting, ready, or failed. Handshake errors and terminal closes
stop retries. Incoming/pre-auth/outgoing queues and WebSocket buffered bytes are
bounded; overflow drops datagrams rather than blocking frames or growing memory.
WSS has TCP head-of-line blocking and is not claimed to equal UDP performance.

## Dedicated server build and data handoff

```sh
cmake -S . -B build-dedicated -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_CLIENT=OFF -DBUILD_SERVER=ON -DBUILD_GAME_QVMS=ON
cmake --build build-dedicated --parallel 2
build-dedicated/Release/ioq3ded --version
```

Handoff artifacts are `build-dedicated/Release/ioq3ded` (Linux x86-64) and
`build-dedicated/Release/baseq3/vm/{qagame,cgame,ui}.qvm`. Keep binary artifacts
out of Git and transfer them with checksums to the platform's controlled runtime.
The Linux build is dynamically linked: verify its libc/runtime dependencies on
the actual destination, not merely its architecture.

The data root must contain the authorized `baseq3` package set, including the
selected map, matching AAS/botfiles for Bot play, and the chosen game module
version. Inventory package SHA-256, internal paths, BSP/AAS pairs and the game's
reference version before making the server available. Source game data is not
present in this checkout; **the successful binary build is not a runnable map
or a complete asset manifest**.

After data is provided, a controlled same-host native gateway launch uses:

```sh
build-dedicated/Release/ioq3ded \
  +set dedicated 1 +set net_enabled 1 +set net_ip 127.0.0.1 +set net_port 27960 \
  +set fs_basepath "$AUTHORIZED_DATA_ROOT" +set fs_homepath "$WRITABLE_HOME" \
  +set sv_master1 "" +set sv_master2 "" +set sv_master3 "" \
  +set sv_master4 "" +set sv_master5 "" +set sv_pure 1 \
  +set sv_maxclients 8 +set g_gametype 0 +set timelimit 10 +set fraglimit 30 \
  +map "$AUTHORIZED_MAP"
```

Do not change the reference server tick just to match the display refresh rate.
Do not expose RCON or an arbitrary UDP proxy. Bind to a private interface only
when the gateway runtime topology requires it, and enforce the service whitelist.
Use the platform's supervised process/container runner rather than backgrounding
this command in an ephemeral shell. Live service deployment remains subject to
the existing test and compatibility gates, within the user's authorization.

## Verification and limits

```sh
node --test misc/tests/net-websocket.test.mjs
python3 misc/tests/web-persistence.test.py
python3 misc/tests/web-frame.test.py
```

The network test executes the production EM_JS bodies with a controlled socket,
clock and WASM heap. It verifies auth ordering, byte copies, message boundaries,
size limits, backpressure, reconnection, stale callbacks and invalid credentials.
The persistence test compiles production close/open functions and injects open,
write and close errors: only completed home config/state writes notify the host.
The frame test compiles production screen functions with a stub renderer/VM and
checks that notifications follow frame submission, excluding connecting/loading
overlays even when UI input is captured. These tests do not substitute for a real
browser-to-native-server match.

Release still requires platform service + actual browser interoperability,
multiple players, original rule/packet correctness, bad-network tests, session
expiry/rejoin and representative hardware performance. Run those with authorized
data; do not claim a generated test room completes original-map reproduction.
