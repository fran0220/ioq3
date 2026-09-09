// SPDX-License-Identifier: GPL-2.0-or-later
// Packages are supplied by the authorized asset pipeline, never downloaded here.
import { readdir, readFile, writeFile, lstat } from 'node:fs/promises';
import { resolve, relative, sep } from 'node:path';
import { createHash } from 'node:crypto';
import { validateManifest } from './host.mjs';

const [directory, basegame = 'baseq3'] = process.argv.slice(2);
if (!directory || !/^[a-z0-9_-]+$/i.test(basegame)) throw new Error('Usage: node code/web/make-manifest.mjs <Web Release directory> [basegame]');
const root = resolve(directory);
const files = [];
async function scan(dir) {
    for (const name of (await readdir(dir)).sort()) {
        const path = resolve(dir, name);
        const stat = await lstat(path);
        if (stat.isSymbolicLink()) throw new Error('Asset symlinks are not allowed');
        if (stat.isDirectory()) await scan(path);
        else if (/\.(pk3|qvm)$/.test(name)) {
            const data = await readFile(path);
            files.push({ path: relative(root, path).split(sep).join('/'), bytes: data.length,
                sha256: createHash('sha256').update(data).digest('hex') });
        }
    }
}
await scan(resolve(root, basegame));
if (!files.some(f => f.path.endsWith('.pk3'))) throw new Error('No PK3 installed. QVM binaries alone do not make a playable game.');
const revision = createHash('sha256').update(JSON.stringify(files)).digest('hex');
const manifest = validateManifest({ schemaVersion: 1, revision, basegame, files });
await writeFile(resolve(root, 'game-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`Manifest: ${files.length} verified files, revision ${revision}`);
