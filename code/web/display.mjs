// SPDX-License-Identifier: GPL-2.0-or-later
// Fixed launch-time choices, never a console-command interface.
export const displayPresets = Object.freeze({
    balanced: Object.freeze({ label: 'Balanced · 720p / reduced textures', width: 1280, height: 720, picmip: 1 }),
    high: Object.freeze({ label: 'High · 1080p / full textures', width: 1920, height: 1080, picmip: 0 }),
    native: Object.freeze({ label: 'Desktop resolution / full textures', picmip: 0 }),
});

export function displayArguments(preset) {
    if (preset === null) return []; // Preserve existing advanced engine settings.
    if (!Object.hasOwn(displayPresets, preset)) throw new Error('Unknown display preset.');
    const value = displayPresets[preset];
    return ['+set', 'r_picmip', String(value.picmip), '+set', 'r_mode', value.width ? '-1' : '-2',
        ...(value.width ? ['+set', 'r_customwidth', String(value.width), '+set', 'r_customheight', String(value.height)] : [])];
}

// Root-owned timer survives a broken engine. A preview never changes saved data
// until the player confirms; replacement without a preset restores saved settings.
export function createDisplayPreview({ replace, confirm, report, schedule = setTimeout, cancel = clearTimeout }) {
    let state = 'idle', timer = null, generation = 0, mounting = Promise.resolve();
    const emit = (next, detail = '') => { state = next; report({ state, detail }); };
    const clear = () => { cancel(timer); timer = null; };
    async function rollback() {
        if (state === 'idle' || state === 'rolling-back') return;
        clear();
        const mine = ++generation;
        emit('rolling-back');
        await mounting.catch(() => {});
        if (mine !== generation) return;
        try {
            await replace(null);
            if (mine === generation) emit('idle', 'Previous saved display settings restored.');
        } catch {
            if (mine === generation) emit('idle', 'Could not restart the engine. Retry uses the previous saved settings.');
        }
    }
    return {
        async preview(preset) {
            displayArguments(preset);
            if (preset === null || state !== 'idle') throw new Error('Display preview unavailable.');
            const mine = ++generation;
            emit('starting');
            timer = schedule(() => void rollback(), 120000);
            try { mounting = Promise.resolve(replace(preset)); await mounting; }
            catch { if (mine === generation) await rollback(); }
        },
        ready() {
            if (state !== 'starting') return;
            clear(); emit('preview');
            timer = schedule(() => void rollback(), 15000);
        },
        failed() { if (state === 'starting' || state === 'preview') void rollback(); },
        async accept() {
            if (state !== 'preview') return false;
            clear();
            const mine = generation;
            emit('confirming');
            try {
                await confirm();
                if (mine !== generation) return false;
                emit('idle', 'Display settings confirmed and saved.');
                return true;
            } catch {
                if (mine === generation) await rollback();
                return false;
            }
        },
        rollback,
        abandon() { clear(); ++generation; emit('idle'); },
        get state() { return state; },
    };
}
