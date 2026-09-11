// SPDX-License-Identifier: GPL-2.0-or-later
// DOM navigation never signals game readiness and never accepts console text.
import { createHUD, readHUD, matchClock, teamNames } from './hud.mjs';
import { createLobby } from './lobby.mjs';
import { createPlay } from './play.mjs';

// Read-only transport events, not session admission or Quake match readiness.
export function networkNotice(state) {
    switch (state) {
    case 'admitting': return 'Requesting admission. No transport connection yet.';
    case 'connecting': return 'Connecting transport. The game handshake is still required.';
    // Inner host reports transport `ready`; the outer shell normalizes it.
    case 'ready':
    case 'connected': return '';
    case 'reconnecting': return 'Connection interrupted — reconnecting with the existing session.';
    case 'failed': return 'Connection failed. Open Rooms / engine to retry with a fresh engine.';
    case 'closed': return 'Transport closed. Open Rooms / engine or start a local match.';
    default: return undefined;
    }
}

export function createMenu(canvas) {
    const root = document.querySelector('#menu');
    // The toolbar wraps at short PC widths. Reserve its measured height so
    // scrolling/focused fields never disappear behind fixed controls.
    new ResizeObserver(([entry]) => {
        document.documentElement.style.setProperty('--controls-height', `${entry.target.getBoundingClientRect().height}px`);
    }).observe(document.querySelector('#controls'));
    const hud = createHUD(document.querySelector('#hud'));
    const lobby = createLobby(window.OG);
    const displayQuality = document.querySelector('#display-quality');
    displayQuality.disabled = typeof window.IOQ3_BOOT?.openDisplay !== 'function';
    if (!displayQuality.disabled) document.querySelector('#display-quality-note').textContent =
        'Open display quality in Rooms / engine. Preview restarts the engine; Keep saves, while Revert or the 15-second timeout restores the previous settings.';
    displayQuality.addEventListener('click', () => window.IOQ3_BOOT?.openDisplay?.());
    const tell = text => { for (const node of root.querySelectorAll('.edit-status')) node.textContent = text; };
    const saving = () => { document.querySelector('#save-status').textContent = 'Applied — waiting for engine save…'; };
    let module, ready = false, failed = false, snapshot, heldAction = null;
    const state = () => ready && !failed ? module?._OG_WebUIState?.() ?? 0 : 0;
    // Accepted launch already releases engine menu ownership; it may enter
    // connecting state before JS regains control. Do not call the UI VM twice.
    const play = createPlay(() => module, hideMenu);
    function frame() {
        if (failed) return;
        snapshot = ready && !document.hidden ? readHUD(module) : null;
        hud.render(snapshot, !root.hidden);
        // Renew only after a successful render. Runtime/DOM failures naturally
        // stop this loop and the engine's one-second lease restores native HUD.
        if (ready) module?._OG_WebHUDEnabled?.(snapshot && root.hidden ? 1 : 0);
        if (!root.hidden && !root.querySelector('[data-page="match"]').hidden) refreshMatch();
        requestAnimationFrame(frame);
    }
    function releaseAction() {
        if (heldAction === null) return;
        module?._OG_WebMatchAction?.(heldAction, 0);
        heldAction = null;
    }
    function holdAction(id) {
        if (state() !== 2) return;
        close();
        if (!root.hidden) return;
        if (module._OG_WebMatchAction?.(id, 1) === 1) heldAction = id;
    }
    function refreshMatch() {
        const active = state() === 2 && typeof module?._OG_WebMatchAction === 'function';
        for (const button of root.querySelectorAll('[data-page="match"] button')) button.disabled = !active;
        document.querySelector('#match-respawn').disabled = !active || !snapshot || (snapshot.health > 0 && !snapshot.intermission);
        document.querySelector('#match-summary').textContent = snapshot
            ? `${snapshot.map} · ${teamNames[snapshot.team]} · Score ${snapshot.score} · ${matchClock(snapshot.elapsed)}` : 'No active match.';
    }
    for (const [name, id] of [['match-respawn', 1], ['match-scores', 0]]) {
        document.getElementById(name).addEventListener('pointerdown', event => {
            if (event.button !== 0) return;
            event.preventDefault(); holdAction(id);
        });
    }
    for (const event of ['pointerup', 'pointercancel', 'blur']) window.addEventListener(event, releaseAction, true);
    document.addEventListener('visibilitychange', () => { if (document.hidden) releaseAction(); });
    for (const [name, id] of [['match-restart', 3], ['match-disconnect', 2], ['match-join-team', 4]]) {
        document.getElementById(name).addEventListener('click', () => {
            const arg = id === 4 ? Number(document.querySelector('#match-team').value) : 0;
            if (module?._OG_WebMatchAction?.(id, arg) !== 1) {
                document.querySelector('#match-status').textContent = 'Action rejected. Restart requires a local server; team changes require an active match.';
                return;
            }
            document.querySelector('#match-status').textContent = 'Request sent to the engine. Waiting for authoritative state.';
            if (id !== 2) close();
        });
    }
    const fields = [
        ['Master volume', 0, 0, 1, 0.05], ['Music volume', 1, 0, 1, 0.05],
        ['Mouse sensitivity', 2, 0.1, 30, 0.1], ['Mouse pitch', 3, -0.1, 0.1, 0.001],
        ['Field of view', 4, 60, 140, 1],
        ['Crosshair style', 5, 0, 10, 1, 'display'], ['Crosshair size', 6, 8, 64, 1, 'display'],
        ['Show FPS (0 / 1)', 7, 0, 1, 1, 'display'],
        ['Handicap', 8, 1, 100, 1, 'profile'], ['Primary color', 9, 1, 7, 1, 'profile'], ['Secondary color', 10, 1, 7, 1, 'profile'],
    ];
    for (const [label, id, min, max, step, group = 'setting'] of fields) {
        const row = document.createElement('label');
        row.className = 'setting-row';
        const name = document.createElement('span');
        name.textContent = label;
        const input = document.createElement('input');
        Object.assign(input, { type: 'number', min, max, step, id: `setting-${id}` });
        input.placeholder = 'Unavailable';
        input.addEventListener('change', () => {
            const value = input.valueAsNumber;
            const previous = [1, 2].includes(state()) ? module._OG_WebSetting(id) : NaN;
            if (!input.checkValidity() || !Number.isFinite(value) || ![1, 2].includes(state())
                || !module._OG_WebSetSetting(id, value)) {
                tell('Engine rejected this value. No successful change is claimed.');
            } else {
                tell(`${label} applied: ${module._OG_WebSetting(id)}. Browser save status appears below.`);
                if (value !== previous) saving();
            }
            refresh();
        });
        row.append(name, input);
        document.querySelector(`#${group}-fields`).append(row);
    }
    const pitchNote = document.createElement('p');
    pitchNote.className = 'note';
    pitchNote.textContent = 'Negative mouse pitch inverts vertical look. Zero is rejected.';
    document.querySelector('#setting-fields').append(pitchNote);
    const filter = document.querySelector('#texture-filter');
    filter.addEventListener('change', () => {
        const choice = Number(filter.value);
        if (![1, 2].includes(state()) || module._OG_WebTextureFilter(choice) !== choice) tell('Texture filter change rejected.');
        else { tell('Texture filtering applied to the renderer.'); saving(); }
    });
    function readName() {
        let result = '';
        for (let i = 0; i < 31; i++) {
            const code = module._OG_WebName(3, i);
            if (code <= 0) break;
            result += String.fromCharCode(code);
        }
        return result;
    }
    document.querySelector('#profile-form').addEventListener('submit', event => {
        event.preventDefault();
        if (![1, 2].includes(state())) return;
        const value = document.querySelector('#player-name').value;
        const previous = readName();
        module._OG_WebName(0, 0);
        for (const character of value) module._OG_WebName(1, character.codePointAt(0));
        if (module._OG_WebName(2, 0) !== 1) tell('Name rejected. Keep 1–31 printable ASCII characters and omit the listed delimiters.');
        else { tell(`Player name applied: ${readName()}.`); if (value !== previous) saving(); }
    });
    const actions = ['Forward', 'Back', 'Strafe left', 'Strafe right', 'Jump', 'Crouch', 'Walk', 'Fire', 'Zoom', 'Scores',
        'Previous weapon', 'Next weapon', 'Use item', 'Chat', 'Team chat', 'Gauntlet', 'Machinegun', 'Shotgun',
        'Grenade launcher', 'Rocket launcher', 'Lightning gun', 'Railgun', 'Plasma gun', 'BFG', 'Center view',
        'Strafe modifier', 'Turn left', 'Turn right', 'Look up', 'Look down'];
    const specialNames = ['Tab', 'Enter', 'Backspace', 'Caps lock', 'Up', 'Down', 'Left', 'Right', 'Alt', 'Ctrl', 'Shift',
        'Insert', 'Delete', 'Page down', 'Page up', 'Home', 'End', ...Array.from({ length: 9 }, (_, i) => `F${i + 1}`),
        'Mouse 1', 'Mouse 2', 'Mouse 3', 'Mouse 4', 'Mouse 5', 'Wheel down', 'Wheel up',
        'Numpad 7', 'Numpad 8', 'Numpad 9', 'Numpad 4', 'Numpad 5', 'Numpad 6', 'Numpad 1', 'Numpad 2', 'Numpad 3',
        'Numpad Enter', 'Numpad 0', 'Numpad decimal', 'Numpad /', 'Numpad -', 'Numpad +', 'Num lock', 'Numpad *', 'Numpad ='];
    let pendingBinding;
    const conflict = document.querySelector('#binding-conflict');
    function refreshBindings() {
        const list = document.querySelector('#binding-fields');
        const position = list.scrollTop;
        list.replaceChildren();
        if (![1, 2].includes(state())) return;
        const keys = [];
        for (let i = 0; i < 95 + specialNames.length; i++) {
            const key = module._OG_WebKey(i), action = module._OG_WebBinding(key);
            if (action !== -3) keys.push({ key, action, label: i < 95 ? (key === 32 ? 'Space' : String.fromCharCode(key)) : specialNames[i - 95] });
        }
        actions.forEach((name, action) => {
            const row = document.createElement('div'); row.className = 'binding-row';
            row.dataset.action = action;
            const title = document.createElement('span'); title.textContent = name; row.append(title);
            const slots = keys.filter(key => key.action === action).map(key => key.key).concat(-1);
            slots.forEach((old, slot) => {
                const select = document.createElement('select');
                select.id = `binding-${action}-${slot}`;
                select.setAttribute('aria-label', `${name} ${old === -1 ? 'add binding' : `binding ${slot + 1}`}`);
                select.append(new Option(old === -1 ? 'Add binding…' : 'Unbound', '-1'));
                for (const item of keys) {
                    const option = new Option(item.label + (item.action === -2 ? ' (custom)' : ''), item.key);
                    option.disabled = item.action === -2; select.append(option);
                }
                select.value = String(old);
                select.addEventListener('change', () => {
                    const next = Number(select.value);
                    const result = module._OG_WebBind(action, old, next, 0);
                    pendingBinding = null; conflict.hidden = true;
                    tell('');
                    if (result === 2) {
                        const target = module._OG_WebBinding(next);
                        pendingBinding = { action, old, next, target };
                        document.querySelector('#binding-conflict-text').textContent = `This key is assigned to ${actions[target]}. Replace that assignment with ${name}?`;
                        conflict.hidden = false;
                        document.querySelector('#binding-replace').focus();
                    } else if (result === 1) { tell(`${name} binding applied.`); saving(); }
                    else tell('Binding rejected. Custom commands and stale slots are protected.');
                    refreshBindings();
                    if (result !== 2) focusBinding(action, result === 1 ? next : old);
                });
                row.append(select);
            });
            list.append(row);
        });
        list.scrollTop = position;
    }
    function focusBinding(action, key) {
        const selects = [...root.querySelectorAll(`[data-action="${action}"] select`)];
        (selects.find(select => select.value === String(key)) ?? selects[0])?.focus({ preventScroll: true });
    }
    document.querySelector('#binding-cancel').addEventListener('click', () => {
        const p = pendingBinding; pendingBinding = null; conflict.hidden = true; tell('Binding change cancelled.');
        if (p) focusBinding(p.action, p.old);
    });
    document.querySelector('#binding-replace').addEventListener('click', () => {
        const p = pendingBinding; pendingBinding = null; conflict.hidden = true;
        if (p && module._OG_WebBinding(p.next) === p.target && module._OG_WebBind(p.action, p.old, p.next, 1) === 1) {
            tell(`${actions[p.action]} binding applied; conflicting assignment replaced.`); saving();
        } else tell('Binding state changed. Choose the key again.');
        refreshBindings();
        if (p) focusBinding(p.action, p.next);
    });
    function refresh() {
        for (const [, id] of fields) {
            const input = document.querySelector(`#setting-${id}`);
            const value = [1, 2].includes(state()) ? module._OG_WebSetting(id) : NaN;
            input.disabled = !Number.isFinite(value);
            input.value = Number.isFinite(value) ? Number(value.toFixed(3)) : '';
        }
    }
    function screen(name) {
        for (const page of root.querySelectorAll('[data-page]')) page.hidden = page.dataset.page !== name;
        for (const button of root.querySelectorAll('[data-screen]')) {
            if (button.dataset.screen === name) button.setAttribute('aria-current', 'page');
            else button.removeAttribute('aria-current');
        }
        tell(''); pendingBinding = null; conflict.hidden = true;
        if (['settings', 'display', 'profile'].includes(name)) refresh();
        if (name === 'display') filter.value = String(module._OG_WebTextureFilter(-1));
        if (name === 'profile') document.querySelector('#player-name').value = readName();
        if (name === 'bindings') refreshBindings();
        if (name === 'match') refreshMatch();
        if (name === 'play' || name === 'profile') play.refresh();
        lobby.show(name === 'lobby');
        root.querySelector(`[data-page="${name}"] h2`).focus();
    }
    function open() {
        const current = state();
        if (![1, 2].includes(current) || !module._OG_WebMenu(1)) return;
        releaseAction();
        if (document.pointerLockElement) document.exitPointerLock();
        root.hidden = false;
        canvas.inert = true;
        document.querySelector('#menu-context').textContent = current === 2 ? 'IN-MATCH / MENU' : 'ARENA SYSTEMS / STANDBY';
        document.querySelector('#menu-title').innerText = current === 2 ? 'TAKE A\nBREATH.' : 'MAKE EVERY\nMOVE COUNT.';
        document.querySelector('#play').textContent = current === 2 ? 'Resume match →' : 'Choose your arena →';
        document.querySelector('#play-note').textContent = current === 2
            ? 'Local single-player may pause. Online matches continue while this menu is open.'
            : 'Select an installed arena, game mode, opponents and character. Local play needs no online account.';
        screen('home');
    }
    function close() {
        const current = state();
        if (![1, 2].includes(current) || !module._OG_WebMenu(current === 1 ? 2 : 0)) return;
        hideMenu();
    }
    function hideMenu() {
        root.hidden = true;
        lobby.show(false);
        canvas.inert = false;
        canvas.focus();
    }
    for (const button of root.querySelectorAll('[data-screen]')) button.addEventListener('click', () => screen(button.dataset.screen));
    document.querySelector('#open-menu').addEventListener('click', open);
    document.querySelector('#play').addEventListener('click', () => state() === 2 ? close() : screen('play'));
    document.querySelector('#return-engine').addEventListener('click', close);
    document.querySelector('#capture').addEventListener('click', () => { if (!root.hidden) close(); });
    // Capture before SDL's document handlers, so DOM typing/navigation cannot
    // activate hidden engine menu items or move/fire in the match.
    for (const type of ['keydown', 'keyup', 'keypress']) window.addEventListener(type, event => {
        const hold = { 'match-respawn': 1, 'match-scores': 0 }[event.target.id];
        if ((event.key === 'Enter' || event.key === ' ') && (hold !== undefined || heldAction !== null)) {
            event.preventDefault(); event.stopImmediatePropagation();
            if (type === 'keydown' && !event.repeat && hold !== undefined) holdAction(hold);
            if (type === 'keyup') releaseAction();
        } else if (!root.hidden && event.key === 'Tab' && type === 'keydown') {
            // Keep keyboard navigation in the visible menu and persistent
            // toolbar; never send focus into the covered canvas or live HUD.
            const focusable = [...document.querySelectorAll('#menu button, #menu input, #menu select, #menu [tabindex="0"], #controls button')]
                .filter(node => !node.disabled && node.getClientRects().length);
            const first = focusable[0], last = focusable.at(-1);
            if (event.shiftKey && (document.activeElement === first || !focusable.includes(document.activeElement))) {
                event.preventDefault(); last?.focus();
            } else if (!event.shiftKey && (document.activeElement === last || !focusable.includes(document.activeElement))) {
                event.preventDefault(); first?.focus();
            }
            event.stopImmediatePropagation();
        } else if (event.key === 'F10' || (!root.hidden && event.key === 'Escape')) {
            event.preventDefault(); event.stopImmediatePropagation();
            if (type === 'keydown' && !event.repeat) root.hidden ? open() : close();
        } else if (!root.hidden) event.stopImmediatePropagation();
    }, true);
    return {
        attach(value) { module = value; requestAnimationFrame(frame); },
        report(update) {
            const notice = document.querySelector('#connection-notice');
            const message = networkNotice(update.network);
            if (message !== undefined && !failed) {
                notice.textContent = message;
                notice.hidden = !message;
            }
            if (update.state === 'failed') {
                notice.hidden = true;
                releaseAction(); hud.hide(); lobby.stop();
                failed = true; root.hidden = true;
                canvas.inert = true;
                // An aborted runtime may reject calls; it cannot process input
                // again and full reload will reset its static ownership flag.
                try { module?._OG_WebMenu?.(3); } catch { /* Reload is required. */ }
            }
            // Leave the engine frame stack before calling back into its UI VM.
            if (update.state === 'ready' && !ready) { ready = true; queueMicrotask(open); }
        },
    };
}
