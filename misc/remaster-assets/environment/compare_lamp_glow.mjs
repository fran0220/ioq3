// Same engine, QVM, camera and lighting; swap only the candidate scene package.
import { copyFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { connect, sleep } from '../../tests/gameplay/browser.mjs';
const [cdp, fixturePackage, originalPackage, glowPackage, out] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const b = await connect(cdp, `${out}/journal.jsonl`);
const results = [];
try {
    const base = await b.evaluate('location.origin');
    for (const [variant, source] of [['without', originalPackage], ['with', glowPackage]]) {
        copyFileSync(source, fixturePackage);
        await b.send('Page.navigate', { url: `${base}/?scene=1&hdr=0&ab=${variant}` });
        await sleep(500);
        await b.waitFor(() => b.evaluate('window.readEngine?.()'), s => s?.state === 8 && s.snap.valid, 60000);
        await b.evaluate('document.querySelector("canvas").focus()');
        for (const [name, command] of [['east', 'setviewpos 1110 1020 76 0'], ['west', 'setviewpos 234 1020 76 180']]) {
            await b.command(command);
            await sleep(1500);
            const state = await b.evaluate('readEngine()');
            b.record('comparison-state', { variant, name, state });
            await b.screenshot(`${out}/${name}-${variant}.jpg`);
            results.push({ variant, source, name, state });
        }
    }
} finally {
    writeFileSync(`${out}/results.json`, JSON.stringify(results, null, 2));
    await b.close();
}
