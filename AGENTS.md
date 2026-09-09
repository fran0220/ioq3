# Origin Game attached project

This repository is an Origin Game game project. Its Amp project is
`doufunao/ioq3`; the platform source of truth is `fran0220/origingame`.
The current task is project preparation, not publication. Do not publish a
game, invoke paid model/artwork generation, or deploy platform infrastructure
without explicit authorization.

## Publishing identity and environment

- Keep the creator selected in the root `.origingame-deploy.json`. It was
  randomly selected once from the platform account pool; do not reselect it
  when an orb starts or when the game changes.
- Project secrets supply the selected `OG_CREATOR_KEY_<HANDLE>` and a default
  `OG_API_KEY`. `OG_HOST` and `OG_AI_GATEWAY` supply portal and direct AI
  Gateway origins. Never commit credentials or include them in web artifacts.
- Personal Amp variables override project variables. Do not assume a bare
  `OG_API_KEY` belongs to this game's publisher. Use the platform deploy
  helper with `--identity "$PWD/.origingame-deploy.json"`; its creator
  selection uses the named key and fails if that key is missing. `OG_CREATOR`
  alone is attribution, not authentication.
- Use the root identity even when publishing a disposable build directory.
  After the first authorized publish, commit its returned game ID and URLs
  so subsequent releases update the same game. No game ID exists before then.
- Read the current platform `skill/origingame-deploy/SKILL.md`,
  `skill/origingame-deploy/scripts/deploy.sh`, and `docs/origin-gateway.md`
  before integration or release. Long AI streams use the direct Gateway;
  game publication uses the portal. Never expose a Gateway key to browser code.
- Publishing a game does not require platform SSH, database, Cloudflare, or
  storage administrator credentials.

## Work still required before release

The orb currently configures a native Debug build in `build-orb`:
`cmake --build build-orb --parallel 2`. This is not a publishable browser game.
The existing Web CI pins Emscripten 3.1.58; preserve that version when preparing
the Web toolchain unless an upgrade is deliberately verified.

Before publishing, build and test the browser version, provide root
`index.html` with relative asset paths, integrate platform loading/readiness
and fullscreen APIs, and validate both standalone and platform-embedded play.
Follow platform artifact, artwork, preflight, identity, and post-publish checks.
The current Web template disables networking; the AI Gateway is not a Quake
multiplayer transport.

ioq3 engine code is GPL-licensed, but commercial Quake 3 game data is not
provided or licensed by this repository. Establish redistribution rights for
all game assets and publish the appropriate license/source information;
do not blindly use the deploy helper's default protected license mode.
