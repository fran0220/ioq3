// SPDX-License-Identifier: GPL-2.0-or-later
// Extend the existing private gameplay host with explicit local content packs.
import { execFileSync } from 'node:child_process';
import { cpSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const [release, demo, outputArg, ...packs] = process.argv.slice(2);
if (!outputArg) throw Error('Usage: node prepare.mjs WEB_RELEASE DEMO NEW_OUTPUT PACK.pk3...');
const names = ['pak0.pk3', 'zz-ioq3-vm.pk3', ...packs.map(pack => basename(pack))];
if (new Set(names).size !== names.length) throw Error('Duplicate pack basename');
execFileSync(process.execPath, [fileURLToPath(new URL('../gameplay/prepare.mjs', import.meta.url)),
    release, demo, outputArg], { stdio: 'inherit' });
const output = resolve(outputArg);
const hostPath = join(output, 'index.html');
const host = readFileSync(hostPath, 'utf8');
const original = "['pak0.pk3', 'zz-ioq3-vm.pk3']";
if (!host.includes(original)) throw Error('Gameplay host pack contract changed');
writeFileSync(hostPath, host.replace(original, JSON.stringify(names)));
const receiptPath = join(output, 'technical-fixture.json');
const receipt = JSON.parse(readFileSync(receiptPath));
for (const pack of packs) {
    const name = 'demoq3/' + basename(pack);
    cpSync(pack, join(output, name));
    receipt.hashes[name] = createHash('sha256').update(readFileSync(pack)).digest('hex');
}
receipt.hashes['index.html'] = createHash('sha256').update(readFileSync(hostPath)).digest('hex');
writeFileSync(receiptPath, JSON.stringify(receipt, null, 2));
