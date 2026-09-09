// SPDX-License-Identifier: GPL-2.0-or-later
// Copies user-supplied technical demo data. Never downloads or publishes it.
import { cpSync, mkdirSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const [releaseArg, demoArg, outputArg] = process.argv.slice(2);
if (!outputArg) throw new Error('Usage: node prepare.mjs WEB_RELEASE EXTRACTED_DEMO NEW_OUTPUT_DIR');
const [release, demo, output] = [releaseArg, demoArg, outputArg].map(path => resolve(path));
if (existsSync(output)) throw new Error('Use a new output directory; refusing to mix test data with an existing build');
for (const path of [join(release, 'ioquake3.js'), join(release, 'ioquake3.wasm'),
    join(release, 'baseq3/vm/cgame.qvm'), join(release, 'baseq3/vm/qagame.qvm'),
    join(release, 'baseq3/vm/ui.qvm'), join(demo, 'demoq3/pak0.pk3'), join(demo, 'Help/Q3A_EULA.txt')]) {
    if (!existsSync(path)) throw new Error(`Required input missing: ${path}`);
}
mkdirSync(join(output, 'demoq3'), { recursive: true });
for (const name of ['ioquake3.js', 'ioquake3.wasm']) cpSync(join(release, name), join(output, name));
cpSync(join(demo, 'demoq3/pak0.pk3'), join(output, 'demoq3/pak0.pk3'));
cpSync(join(demo, 'Help'), join(output, 'demo-license-and-help'), { recursive: true });
cpSync(fileURLToPath(new URL('./fixture.html', import.meta.url)), join(output, 'index.html'));
execFileSync('python3', ['-m', 'zipfile', '-c', join(output, 'demoq3/zz-ioq3-vm.pk3'), 'vm'],
    { cwd: join(release, 'baseq3') });
// Demo 1.11 has the pre-missionpack inventory ABI (bullets=16, health=24).
// Current qagame uses bullets=19, health=29 even for baseq3. Without this
// matching GPL header the old bot scripts falsely see no ammunition.
const inventory = fileURLToPath(new URL('../../../code/game/inv.h', import.meta.url));
execFileSync('python3', ['-c',
    'import sys,zipfile; z=zipfile.ZipFile(sys.argv[1],"a"); z.write(sys.argv[2],"botfiles/inv.h"); z.close()',
    join(output, 'demoq3/zz-ioq3-vm.pk3'), inventory]);
const hashes = {};
for (const path of ['ioquake3.js', 'ioquake3.wasm', 'demoq3/pak0.pk3', 'demoq3/zz-ioq3-vm.pk3']) {
    hashes[path] = createHash('sha256').update(readFileSync(join(output, path))).digest('hex');
}
writeFileSync(join(output, 'technical-fixture.json'), JSON.stringify({
    warning: 'Official demo technical test only; do not publish this directory or its assets',
    demoSource: 'https://ftp.gwdg.de/pub/misc/ftp.idsoftware.com/idstuff/quake3/linux/linuxq3ademo-1.11-6.x86.gz.sh',
    botInventoryOverride: {
        source: 'code/game/inv.h', license: 'GPL-2.0-or-later',
        reason: 'Match current qagame inventory ABI without changing gameplay rules or original pak0.pk3',
        sha256: createHash('sha256').update(readFileSync(inventory)).digest('hex'),
    },
    hashes,
}, null, 2));
console.log(`Prepared local technical fixture: ${output}`);
