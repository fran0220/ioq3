// Host-only controls fixture. Not WASM, no game, never copied to the release.
export default async function(options) {
    const state = window.fixture = { blur: 0, audio: 0 };
    if (new URL(location.href).searchParams.has('hold')) await new Promise(() => {});
    const audio = new AudioContext();
    await audio.suspend();
    state.audioState = () => audio.state;
    state.fail = () => options.onAbort();
    return { ...options, IDBFS: {},
        FS: { mkdirTree() {}, mount() {}, syncfs(populate, cb) { cb(); }, writeFile() {} },
        callMain() {
            // Explicitly labelled fake functional frame to test host controls only.
            options.onEngineFrame({ playable: true, configChanged: false });
        },
        _OG_WebLoseFocus() { state.blur++; },
        _OG_WebResumeAudio() { state.audio++; void audio.resume(); },
    };
}
