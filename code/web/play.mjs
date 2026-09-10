// SPDX-License-Identifier: GPL-2.0-or-later
import { modeNames, playerText } from './hud.mjs';

export const playError = result => ({
    0: 'The engine is not ready for this action.',
    '-1': 'The content catalogue changed. Reopen Play and choose again.',
    '-2': 'The engine rejected these match options. No launch is claimed.',
    '-3': 'Required map, navigation or model assets are missing from this build.',
}[result] ?? 'The engine did not accept the request.');

export function readCatalog(module) {
    const generation = module?._OG_WebCatalogRefresh?.() ?? 0;
    if (generation <= 0) return null;
    const groups = [0, 1, 2].map(kind => Array.from({ length: module._OG_WebCatalogCount(kind) }, (_, index) => {
        const text = field => {
            let value = '';
            for (let i = 0; i < 256; i++) {
                const byte = module._OG_WebCatalogText(kind, index, field, i);
                if (byte <= 0) break;
                value += String.fromCharCode(byte);
            }
            return playerText(value);
        };
        return { id: module._OG_WebCatalogValue(kind, index, 0), modes: module._OG_WebCatalogValue(kind, index, 1),
            available: module._OG_WebCatalogValue(kind, index, 2) === 1, name: text(0), title: text(1) };
    }));
    return { generation, maps: groups[0], bots: groups[1], models: groups[2] };
}

export function createPlay(getModule, launched) {
    const map = document.querySelector('#arena-map'), mode = document.querySelector('#arena-mode');
    const botRoot = document.querySelector('#arena-bots');
    const form = document.querySelector('#match-setup');
    const status = document.querySelector('#play-status');
    const model = document.querySelector('#arena-model');
    const profileModel = document.querySelector('#profile-model');
    const limit = document.querySelector('#arena-limit'), time = document.querySelector('#arena-time');
    let catalog;
    const bots = Array.from({ length: 8 }, (_, slot) => {
        const row = document.createElement('label'); row.className = 'setting-row';
        const select = document.createElement('select'); select.id = `arena-bot-${slot}`;
        row.append(`Bot slot ${slot + 1}`, select); botRoot.append(row);
        return select;
    });
    function fill(select, records, empty) {
        select.replaceChildren();
        if (empty) select.append(new Option(empty, '-1'));
        for (const item of records) {
            const option = new Option(`${item.title || item.name}${item.available ? '' : ' · Missing assets'}`, item.id);
            option.disabled = !item.available; select.append(option);
        }
        select.value = empty ? '-1' : String(records.find(item => item.available)?.id ?? '');
    }
    function updateModes() {
        const selected = catalog?.maps.find(item => item.id === Number(map.value));
        mode.replaceChildren();
        modeNames.forEach((name, id) => {
            if (selected?.modes & (1 << id)) mode.append(new Option(name, id));
        });
        updateRules();
    }
    function updateRules() {
        const single = Number(mode.value) === 2;
        botRoot.hidden = single;
        limit.disabled = time.disabled = single;
        limit.max = Number(mode.value) === 4 ? '100' : '999';
        document.querySelector('#arena-rule-note').textContent = single
            ? 'Single-player uses the original arena roster and limits. Manual bots and limit overrides are disabled.'
            : 'Up to eight fixed bot slots. Tournament/team placement and match rules remain engine-controlled.';
        document.querySelector('#launch-match').disabled = !catalog || !mode.options.length || !map.value;
    }
    function refresh() {
        catalog = readCatalog(getModule());
        document.querySelector('#launch-match').disabled = !catalog;
        for (const button of document.querySelectorAll('[data-apply-model]')) button.disabled = !catalog;
        if (!catalog) {
            status.textContent = 'Installed-content interface unavailable. Return to the engine menu to play; no catalogue or successful launch is fabricated.';
            return;
        }
        fill(map, catalog.maps);
        bots.forEach(select => fill(select, catalog.bots, 'Empty slot'));
        fill(model, catalog.models, 'Keep current character');
        fill(profileModel, catalog.models, 'Choose installed character');
        status.textContent = `${catalog.maps.filter(item => item.available).length} available arenas · ${catalog.bots.filter(item => item.available).length} bots · ${catalog.models.filter(item => item.available).length} character skins.`;
        updateModes();
    }
    map.addEventListener('change', updateModes);
    mode.addEventListener('change', updateRules);
    document.querySelector('#arena-refresh').addEventListener('click', refresh);
    function reject(result) {
        // Some staged fields may already exist after a later validation fails.
        // Require a fresh transaction rather than silently carrying FFA limits
        // into an original-roster single-player launch.
        catalog = null;
        document.querySelector('#launch-match').disabled = true;
        status.textContent = `${playError(result)} Use Refresh content to reset staged options.`;
    }
    for (const button of document.querySelectorAll('[data-apply-model]')) button.addEventListener('click', () => {
        const select = button.dataset.applyModel === 'profile' ? profileModel : model;
        const target = button.dataset.applyModel === 'profile' ? document.querySelector('#model-status') : status;
        if (!catalog || Number(select.value) < 0) { target.textContent = 'Choose an installed character first.'; return; }
        const result = getModule()._OG_WebSelectModel(catalog.generation, Number(select.value));
        target.textContent = result === 1 ? 'Character applied by the engine. Team skins still follow match rules.' : playError(result);
    });
    form.addEventListener('submit', event => {
        event.preventDefault();
        if (!catalog || !form.checkValidity()) return;
        const module = getModule(), generation = catalog.generation;
        const single = Number(mode.value) === 2;
        for (let slot = 0; slot < bots.length; slot++) {
            const result = module._OG_WebPlayBot(generation, slot, single ? -1 : Number(bots[slot].value));
            if (result !== 1) { reject(result); return; }
        }
        if (!single) {
            const result = module._OG_WebPlayLimits(generation, limit.valueAsNumber, time.valueAsNumber);
            if (result !== 1) { reject(result); return; }
        }
        const result = module._OG_WebPlay(generation, Number(map.value), Number(mode.value), Number(document.querySelector('#arena-skill').value));
        if (result !== 1) { reject(result); return; }
        status.textContent = 'Launch accepted. Waiting for the engine to load the arena.';
        launched();
    });
    return { refresh };
}
