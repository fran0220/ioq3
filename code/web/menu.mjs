// SPDX-License-Identifier: GPL-2.0-or-later
// DOM navigation never signals game readiness and never accepts console text.
export function createMenu(canvas) {
    const root = document.querySelector('#menu');
    const status = document.querySelector('#setting-status');
    let module, ready = false, failed = false;
    const state = () => ready && !failed ? module?._OG_WebUIState?.() ?? 0 : 0;
    const fields = [
        ['Master volume', 0, 0, 1, 0.05], ['Music volume', 1, 0, 1, 0.05],
        ['Mouse sensitivity', 2, 0.1, 30, 0.1], ['Mouse pitch', 3, -0.1, 0.1, 0.001],
        ['Field of view', 4, 60, 140, 1],
    ];
    for (const [label, id, min, max, step] of fields) {
        const row = document.createElement('label');
        row.className = 'setting-row';
        const name = document.createElement('span');
        name.textContent = label;
        const input = document.createElement('input');
        Object.assign(input, { type: 'number', min, max, step, id: `setting-${id}` });
        input.addEventListener('change', () => {
            const value = input.valueAsNumber;
            if (!input.checkValidity() || !Number.isFinite(value) || ![1, 2].includes(state())
                || !module._OG_WebSetSetting(id, value)) {
                status.textContent = 'Engine rejected this value. No successful change is claimed.';
            } else status.textContent = `${label} applied: ${module._OG_WebSetting(id)}. Browser save status appears below.`;
            refresh();
        });
        row.append(name, input);
        document.querySelector('#setting-fields').append(row);
    }
    const pitchNote = document.createElement('p');
    pitchNote.className = 'note';
    pitchNote.textContent = 'Negative mouse pitch inverts vertical look. Zero is rejected.';
    document.querySelector('#setting-fields').append(pitchNote);
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
        if (name === 'settings') refresh();
        root.querySelector(`[data-page="${name}"] h2`).focus();
    }
    function open() {
        const current = state();
        if (![1, 2].includes(current) || !module._OG_WebMenu(1)) return;
        if (document.pointerLockElement) document.exitPointerLock();
        root.hidden = false;
        document.querySelector('#menu-context').textContent = current === 2 ? 'IN-MATCH / MENU' : 'ARENA SYSTEMS / STANDBY';
        document.querySelector('#menu-title').innerText = current === 2 ? 'TAKE A\nBREATH.' : 'MAKE EVERY\nMOVE COUNT.';
        document.querySelector('#play').textContent = current === 2 ? 'Resume match →' : 'Open engine Play menu →';
        document.querySelector('#play-note').textContent = current === 2
            ? 'Local single-player may pause. Online matches continue while this menu is open.'
            : 'Map, bot and match selection currently use the original engine menu.';
        screen('home');
    }
    function close() {
        const current = state();
        if (![1, 2].includes(current) || !module._OG_WebMenu(current === 1 ? 1 : 0)) return;
        root.hidden = true;
        canvas.focus();
    }
    for (const button of root.querySelectorAll('[data-screen]')) button.addEventListener('click', () => screen(button.dataset.screen));
    document.querySelector('#open-menu').addEventListener('click', open);
    document.querySelector('#play').addEventListener('click', close);
    document.querySelector('#return-engine').addEventListener('click', close);
    // Capture before SDL's document handlers, so DOM typing/navigation cannot
    // activate hidden engine menu items or move/fire in the match.
    for (const type of ['keydown', 'keyup', 'keypress']) window.addEventListener(type, event => {
        if (event.key === 'F10' || (!root.hidden && event.key === 'Escape')) {
            event.preventDefault(); event.stopImmediatePropagation();
            if (type === 'keydown' && !event.repeat) root.hidden ? open() : close();
        } else if (!root.hidden) event.stopPropagation();
    }, true);
    return {
        attach(value) { module = value; },
        report(update) {
            if (update.state === 'failed') { failed = true; root.hidden = true; }
            if (update.state === 'ready' && !ready) { ready = true; open(); }
        },
    };
}
