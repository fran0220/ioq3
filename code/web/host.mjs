// SPDX-License-Identifier: GPL-2.0-or-later
// No game assets, credentials or URL-provided console commands live in this host.
export const HOME = '/home/players';

export function validateManifest(manifest) {
    if (manifest?.schemaVersion !== 1 || typeof manifest.basegame !== 'string' || !/^[a-z0-9_-]+$/i.test(manifest.basegame)
        || ['home', 'tmp', 'dev', 'proc'].includes(manifest.basegame)
        || !Array.isArray(manifest.files) || typeof manifest.revision !== 'string') {
        throw new Error('Invalid game manifest (expected schemaVersion 1, basegame, revision and files).');
    }
    const paths = new Set();
    for (const file of manifest.files) {
        // Relative, same-origin, literal paths only. No writes into the persistent home.
        if (typeof file.path !== 'string' || !/^[a-z0-9_./-]+$/i.test(file.path)
            || file.path.startsWith('/') || file.path.split('/').some(p => !p || p === '.' || p === '..')
            || !file.path.startsWith(`${manifest.basegame}/`) || paths.has(file.path)
            || !/^[a-f0-9]{64}$/.test(file.sha256) || !Number.isSafeInteger(file.bytes) || file.bytes <= 0) {
            throw new Error('Invalid, duplicate or unsafe asset entry in game manifest.');
        }
        paths.add(file.path);
    }
    return manifest;
}

export function validateSession(session) {
    if (session == null) return null;
    const endpoint = new URL(session.endpoint);
    if (endpoint.protocol !== 'wss:' || endpoint.username || endpoint.password || endpoint.search || endpoint.hash
        || typeof session.token !== 'string' || !session.token || typeof session.sessionId !== 'string'
        || !session.sessionId || session.maxDatagramBytes !== 16384 || session.reconnectGraceMs !== 15000
        || typeof session.expiresAt !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$/.test(session.expiresAt)
        || !Number.isFinite(Date.parse(session.expiresAt)) || Date.parse(session.expiresAt) <= Date.now()) {
        throw new Error('Invalid or expired native multiplayer session.');
    }
    return Object.freeze({ endpoint: endpoint.href, token: session.token, sessionId: session.sessionId,
        expiresAt: session.expiresAt, maxDatagramBytes: 16384, reconnectGraceMs: 15000 });
}

export function engineArguments(basegame, session) {
    return ['+set', 'fs_basepath', '/', '+set', 'fs_homepath', HOME,
        '+set', 'com_basegame', basegame, '+set', 'r_mode', '-2',
        '+set', 'r_fullscreen', '0', '+set', 's_muteWhenUnfocused', '1',
        '+set', 'net_enabled', session ? '1' : '0',
        ...(session ? ['+connect', 'origingame'] : [])];
}

export async function fetchChecked(url, file, fetcher = fetch) {
    const response = await fetcher(url, { cache: 'no-cache', signal: AbortSignal.timeout(120000) });
    if (!response.ok) throw new Error(`Missing asset: ${file.path} (HTTP ${response.status}).`);
    const data = new Uint8Array(await response.arrayBuffer());
    if (data.byteLength !== file.bytes) throw new Error(`Asset size mismatch: ${file.path}.`);
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)),
        b => b.toString(16).padStart(2, '0')).join('');
    if (hash !== file.sha256) throw new Error(`Asset checksum mismatch: ${file.path}.`);
    return data;
}

// One sync at a time; writes arriving during a sync schedule another sync.
// A failed save remains dirty and can be explicitly retried. Never silently
// overwrite existing IndexedDB contents after a failed startup restore.
export function persistence(FS, onStatus) {
    let dirty = false, pending = null, timer = null;
    const sync = populate => new Promise((resolve, reject) => FS.syncfs(populate, e => e ? reject(e) : resolve()));
    const flush = () => {
        clearTimeout(timer);
        timer = null;
        if (pending) return pending;
        if (!dirty) return Promise.resolve();
        pending = (async () => {
            try {
                while (dirty) {
                    dirty = false;
                    onStatus('saving');
                    await sync(false);
                }
                onStatus('saved');
            } catch (error) {
                dirty = true;
                onStatus('failed');
                throw error;
            } finally { pending = null; }
        })();
        return pending;
    };
    return {
        restore: () => sync(true), flush,
        changed() {
            dirty = true;
            if (!pending && !timer) timer = setTimeout(() => {
                timer = null;
                void flush().catch(() => {});
            }, 500);
        },
    };
}

export async function startHost({ factory, canvas, manifestURL, og = null, getSession,
    report = () => {}, onModule = () => {}, fetcher = fetch }) {
    let module, saves, failed = false, ready = false, mainStarted = false;
    const log = [];
    const emit = (state, detail = '') => report({ state, detail, runtimeLoaded: !!module, ready });
    const fail = (code, message) => {
        if (failed) return;
        failed = true;
        emit('failed', message);
        if (typeof og?.loading?.fail === 'function') og.loading.fail({ code, message, retryable: true });
        else og?.loading?.stage?.('Loading failed — reload to retry');
    };
    const frame = ({ playable, configChanged }) => {
        if (failed || !mainStarted) return;
        if (configChanged) saves.changed();
        if (playable && !ready) {
            ready = true;
            emit('ready', 'Click the game to capture the mouse. Esc releases it.');
            og?.loading?.progress?.(1, 'Ready');
            // Ready is sent only by the engine's submitted functional frame hook.
            Promise.resolve(og?.ready?.()).catch(() => {});
        }
    };
    try {
        emit('loading', 'Loading WASM engine');
        og?.loading?.begin?.(['Engine', 'Settings', 'Assets', 'World']);
        og?.loading?.progress?.(0.01, 'Engine');
        module = await factory({ canvas, noInitialRun: true,
            locateFile: path => new URL(path, manifestURL).href,
            onEngineFrame: frame,
            onNativeNetworkStatus: status => report({ network: status.state, code: status.code }),
            print: text => { log.push(String(text)); if (log.length > 30) log.shift(); },
            printErr: text => { log.push(String(text)); if (log.length > 30) log.shift(); },
            onAbort: () => fail('ENGINE_ABORT', 'WASM engine aborted. Reload to retry.'),
            onExit: code => fail('ENGINE_EXIT', `Engine stopped (${code}). ${log.slice(-4).join('\n')}`),
        });
        if (failed) return;
        onModule(module);
        emit('loading', 'WASM loaded; restoring settings');
        og?.loading?.progress?.(0.15, 'Settings');
        module.FS.mkdirTree(HOME);
        module.FS.mount(module.IDBFS, {}, HOME);
        saves = persistence(module.FS, status => report({ persistence: status }));
        await saves.restore();
        const response = await fetcher(manifestURL, { cache: 'no-cache', signal: AbortSignal.timeout(30000) });
        if (!response.ok) throw new Error(`Game manifest unavailable (HTTP ${response.status}).`);
        const manifest = validateManifest(await response.json());
        if (!manifest.files.length) throw new Error('Game data is not installed. Supply authorized PK3 game data and matching cgame/qagame/ui QVMs, then build game-manifest.json.');
        let completed = 0;
        const total = manifest.files.reduce((n, f) => n + f.bytes, 0);
        for (const file of manifest.files) {
            emit('loading', `Checking ${file.path}`);
            const data = await fetchChecked(new URL(file.path, manifestURL), file, fetcher);
            module.FS.mkdirTree(`/${file.path.slice(0, file.path.lastIndexOf('/'))}`);
            module.FS.writeFile(`/${file.path}`, data);
            completed += file.bytes;
            og?.loading?.progress?.(0.2 + 0.65 * completed / total, 'Assets');
        }
        // getSession is a trusted embedding integration, never a query-string source.
        let session;
        try { session = validateSession(await getSession?.()); }
        catch { throw new Error('Unable to acquire a valid multiplayer session. Reload to request a fresh session.'); }
        Object.defineProperty(module, 'ogNetwork', { value: session, writable: false });
        og?.loading?.progress?.(0.9, 'World');
        emit('starting', 'Starting engine; waiting for a playable frame');
        mainStarted = true;
        module.callMain(engineArguments(manifest.basegame, session));
    } catch (error) {
        fail('BOOT_FAILED', error instanceof Error ? error.message : 'Loading failed. Reload to retry.');
    }
    return {
        flush: () => saves?.flush() ?? Promise.resolve(),
        loseFocus() {
            if (mainStarted && !failed) module._OG_WebLoseFocus();
            void saves?.flush().catch(() => {});
        },
        resumeAudio() { if (mainStarted && !failed) module._OG_WebResumeAudio(); },
        fail,
    };
}
