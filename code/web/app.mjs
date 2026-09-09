// SPDX-License-Identifier: GPL-2.0-or-later
import { startHost } from './host.mjs';

const og = window.OG ?? null;
const canvas = document.querySelector('#game');
const status = document.querySelector('#status');
const detail = document.querySelector('#detail');
const retry = document.querySelector('#retry');
const inputStatus = document.querySelector('#input-status');
let host;

function report(update) {
    if (update.state) {
        document.body.dataset.state = update.state;
        document.body.dataset.ready = String(!!update.ready);
        document.body.dataset.runtimeLoaded = String(update.runtimeLoaded);
        status.textContent = { loading: 'Loading', starting: 'Starting engine', ready: 'Ready', failed: 'Unable to start' }[update.state];
        detail.textContent = update.detail;
        retry.hidden = update.state !== 'failed';
        document.querySelector('#controls').hidden = update.state !== 'ready';
    }
    if (update.persistence) document.querySelector('#save-status').textContent = {
        saving: 'Saving…', saved: 'Settings saved', failed: 'Save failed — retry Save settings',
    }[update.persistence];
    if (update.network) document.querySelector('#network-status').textContent = `Network: ${update.network}`;
}

retry.addEventListener('click', () => location.reload());
document.querySelector('#save').addEventListener('click', () => void host?.flush().catch(() => {}));
function resumeAudio() { host?.resumeAudio(); }
window.addEventListener('pointerdown', resumeAudio, { capture: true });
window.addEventListener('keydown', resumeAudio, { capture: true });
document.querySelector('#capture').addEventListener('click', () => {
    canvas.focus();
    resumeAudio();
    try {
        Promise.resolve(canvas.requestPointerLock()).catch(() => {
            inputStatus.textContent = 'Mouse capture denied. Click again to retry.';
        });
    } catch { inputStatus.textContent = 'Mouse capture unavailable in this browser.'; }
});
document.addEventListener('pointerlockchange', () => {
    document.body.dataset.captured = String(document.pointerLockElement === canvas);
    if (document.pointerLockElement !== canvas) host?.loseFocus();
});
document.addEventListener('pointerlockerror', () => {
    inputStatus.textContent = 'Mouse capture denied. Click Capture mouse to retry.';
});
const loseFocus = () => {
    host?.loseFocus();
    if (document.pointerLockElement) document.exitPointerLock();
};
window.addEventListener('blur', loseFocus);
document.addEventListener('visibilitychange', () => { if (document.hidden) loseFocus(); });
canvas.addEventListener('contextmenu', event => event.preventDefault());
canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    host?.fail('CONTEXT_LOST', 'Graphics context lost. Reload to restore the engine.');
});
for (const [id, enable] of [['fullscreen', true], ['exit-fullscreen', false]]) {
    document.getElementById(id).addEventListener('click', async () => {
        try {
            const active = og?.fullscreen ? await og.fullscreen(enable) : await (async () => {
                if (enable && !document.fullscreenElement) await document.documentElement.requestFullscreen();
                if (!enable && document.fullscreenElement) await document.exitFullscreen();
                return !!document.fullscreenElement;
            })();
            inputStatus.textContent = active === enable ? (active ? 'Fullscreen enabled' : 'Fullscreen exited') : 'Fullscreen request denied';
        } catch { inputStatus.textContent = 'Fullscreen unavailable'; }
    });
}

try {
    if (!document.createElement('canvas').getContext('webgl2')) throw new Error('This PC browser requires WebGL2. Enable hardware acceleration or use a supported browser.');
    if (!navigator.locks) throw new Error('Secure browser storage locking is unavailable. Open this game over HTTPS in a supported PC browser.');
    const factory = (await import(document.body.dataset.engine)).default;
    await navigator.locks.request('ioq3-player-home-v1', { ifAvailable: true }, async lock => {
        if (!lock) throw new Error('This game is already open in another tab. Close that tab, then retry to protect your settings.');
        host = await startHost({ factory, canvas, og, report,
            manifestURL: new URL('./game-manifest.json', location.href),
            // Trusted integration may acquire a fresh session; never read credentials
            // from location, archived cvars, localStorage or the asset manifest.
            getSession: window.IOQ3_BOOT?.getSession,
        });
        // Browser releases the exclusive write lease on iframe/tab destruction.
        await new Promise(() => {});
    });
} catch (error) {
    const message = error.message || 'Engine module could not be loaded. Reload to retry.';
    report({ state: 'failed', detail: message, runtimeLoaded: false });
    if (typeof og?.loading?.fail === 'function') og.loading.fail({ code: 'HOST_FAILED', message, retryable: true });
    else og?.loading?.stage?.('Loading failed — reload to retry');
}
