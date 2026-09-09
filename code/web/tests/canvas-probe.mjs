// Real SDL2 fixture on the production template's canvas (never copied to release).
import factory from './canvas-probe.js';
const canvas = document.querySelector('canvas');
const module = await factory({ canvas, locateFile: file => new URL(file, import.meta.url).href });
window.resizeCanvasProbe = () => module._resize_probe();
document.querySelector('#status-panel').hidden = true;
const label = document.createElement('p');
label.textContent = 'REAL SDL2 / WEBGL2 CANVAS PROBE — NOT A GAME';
Object.assign(label.style, { position: 'fixed', top: '16px', left: '24px', color: 'white' });
document.body.append(label);
