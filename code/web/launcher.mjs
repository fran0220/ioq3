// SPDX-License-Identifier: GPL-2.0-or-later
import { createLifecycle } from './lifecycle.mjs';
import { createLobby } from './lobby.mjs';
import { createDisplayPreview, displayPresets } from './display.mjs';

const og = window.OG ?? null;
const slot = document.querySelector('#engine-slot');
const panel = document.querySelector('#room-panel');
const status = document.querySelector('#engine-status');
let attached = null, activeRoom = null, currentBoot = null;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const lifecycle = createLifecycle({ native: og?.native, mount, report(update) {
    if (update.state) {
        document.body.dataset.engineState = update.state;
        status.textContent = { loading: 'Loading engine and verified assets…', starting: 'Starting engine…',
            ready: 'Engine ready.', failed: 'Engine unavailable. Retry or return to local play.', closed: 'Engine stopped.' }[update.state];
        if (currentBoot?.displayPreview != null) {
            if (update.state === 'ready') display.ready();
            if (update.state === 'failed') display.failed();
        }
        if (update.state === 'failed') openLobby();
    }
    if (update.network) {
        document.body.dataset.network = update.network;
        status.textContent = { admitting: 'Requesting this player’s session…', connecting: 'Connecting transport…',
            connected: 'Transport connected. The game must still complete its handshake.',
            reconnecting: 'Reconnecting with the existing session…', failed: 'Connection failed. Retry starts a new engine and session.',
            closed: 'Transport closed locally.' }[update.network];
    }
    if (update.display?.width) {
        const d = update.display;
        document.querySelector('#display-current').textContent = `Renderer: ${d.width} × ${d.height}, texture reduction ${d.picmip}. ${d.preview ? 'Unconfirmed preview.' : 'Current settings.'}`;
    }
} });

const display = createDisplayPreview({
    replace: preset => lifecycle.replace(activeRoom, preset),
    confirm: async () => {
        const engine = attached?.contentWindow?.IOQ3_ENGINE;
        if (!engine) throw new Error('Engine unavailable.');
        await engine.confirmDisplay();
    },
    report(update) {
        document.body.dataset.displayState = update.state;
        document.querySelector('#display-preview').hidden = update.state === 'idle';
        document.querySelector('#display-start').disabled = update.state !== 'idle';
        document.querySelector('#display-keep').disabled = update.state !== 'preview';
        document.querySelector('#display-revert').disabled = ['confirming', 'rolling-back'].includes(update.state);
        document.querySelector('#display-status').textContent = update.detail || {
            starting: 'Starting display preview. Settings are not being saved.',
            preview: 'Keep these display settings? Reverting automatically in 15 seconds.',
            confirming: 'Saving confirmed settings…', 'rolling-back': 'Restoring previous saved settings…',
        }[update.state] || '';
        if (update.state === 'preview') {
            closeLobby();
            document.querySelector('#display-revert').focus();
        }
        if (update.detail) {
            status.textContent = update.detail;
            if (update.state === 'idle') attached?.focus();
        }
    },
});
for (const [id, value] of Object.entries(displayPresets)) {
    const option = document.createElement('option'); option.value = id; option.textContent = value.label;
    document.querySelector('#display-preset').append(option);
}
document.querySelector('#display-start').addEventListener('click', () => {
    closeLobby();
    void display.preview(document.querySelector('#display-preset').value).catch(() => {
        status.textContent = 'An engine transition is already running. Retry when it finishes.';
        openLobby();
    });
});
document.querySelector('#display-keep').addEventListener('click', () => void display.accept());
document.querySelector('#display-revert').addEventListener('click', () => void display.rollback());

function openLobby() {
    attached?.contentWindow?.IOQ3_ENGINE?.pauseInput?.();
    if (!panel.open) panel.showModal();
    lobby.show(true);
}
function closeLobby() { panel.close(); lobby.show(false); attached?.focus(); }
async function start(room = null) {
    display.abandon();
    await lifecycle.replace(room);
    activeRoom = room;
    closeLobby();
}
function requestStart(room = null) {
    void start(room).catch(() => { status.textContent = 'Engine transition failed. Stop the engine and retry.'; });
}

async function mount(boot) {
    const iframe = document.createElement('iframe');
    const controlsSize = new ResizeObserver(entries => {
        if (attached === iframe) document.body.style.setProperty('--engine-controls-height', `${entries[0].target.getBoundingClientRect().height}px`);
    });
    iframe.addEventListener('load', () => {
        const controls = iframe.contentDocument?.querySelector('#controls');
        if (controls) controlsSize.observe(controls);
    });
    iframe.title = 'ioq3 engine';
    iframe.allow = 'autoplay; fullscreen; gamepad';
    iframe.setAttribute('allowfullscreen', '');
    iframe.src = './engine.html';
    currentBoot = boot;
    attached = iframe;
    slot.append(iframe);
    return { boot, async remove() {
        // Bound graceful save; destruction is mandatory even after a crashed
        // child. This is local cleanup, not a server detach acknowledgment.
        try {
            await Promise.race([Promise.resolve(iframe.contentWindow?.IOQ3_ENGINE?.dispose?.()), delay(2000)]);
        } catch { /* Remove the failed child below. */ }
        finally {
            controlsSize.disconnect();
            iframe.remove();
            if (attached === iframe) { attached = null; currentBoot = null; }
        }
        // Let destruction release the child's IndexedDB write lease before mount.
        await delay(0);
    } };
}

// Same-origin functions retain the shell SDK realm. No SDK in the child,
// no forwarding of arbitrary __og messages, and no capabilities in URLs.
Object.defineProperty(window, 'IOQ3_SHELL', { value: Object.freeze({
    attach(child) {
        const boot = currentBoot;
        if (!attached || child !== attached.contentWindow || !lifecycle.isCurrent(boot)) return null;
        const current = () => attached?.contentWindow === child && lifecycle.isCurrent(boot);
        const call = fn => (...args) => { if (current()) return fn?.(...args); };
        const loading = Object.fromEntries(['begin', 'progress', 'stage', 'fail'].map(key => [key, call((...args) => og?.loading?.[key]?.(...args))]));
        return Object.freeze({ ...boot, openLobby: call(openLobby), retry: call(() => requestStart(activeRoom)),
            openDisplay: call(() => {
                openLobby();
                const title = document.querySelector('#display-title');
                title.scrollIntoView({ block: 'center' });
                title.focus({ preventScroll: true });
            }),
            og: Object.freeze({ loading, ready: call(() => og?.ready?.()),
                fullscreen: call(async enable => {
                    if (og?.fullscreen) return og.fullscreen(enable);
                    if (enable && !document.fullscreenElement) await document.documentElement.requestFullscreen();
                    if (!enable && document.fullscreenElement) await document.exitFullscreen();
                    return !!document.fullscreenElement;
                }) }) });
    },
}) });

const lobby = createLobby(og, { enter: start, beforeRelease: async () => {
    display.abandon();
    await lifecycle.stop(); activeRoom = null;
} });
document.querySelector('#open-lobby').addEventListener('click', openLobby);
document.querySelector('#hide-lobby').addEventListener('click', closeLobby);
panel.addEventListener('close', () => lobby.show(false));
document.querySelector('#local-engine').addEventListener('click', () => requestStart());
document.querySelector('#retry-engine').addEventListener('click', () => requestStart(activeRoom));
document.querySelector('#stop-engine').addEventListener('click', () => {
    display.abandon();
    void lifecycle.stop().catch(() => { status.textContent = 'Engine transition already running.'; });
});
requestStart();
