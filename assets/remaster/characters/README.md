# Character production and recovery

`contract.md` freezes the runtime axes, segmented bone/tag boundary and original
Sarge frame mapping. `coverage.json` is a verified Demo subset, not the full
base-game roster. No formal runtime character package has passed acceptance.

The first Painter image is reused by revisions v1 and v2. v1 was submitted under
publisher og-atlas and rejected with HTTP403 before a task ID. Keep that receipt
and private journal. Default generation uses xiaomao; publication stays og-atlas.
The coordinating platform thread separately queried production in READ ONLY at
2026-09-10 05:08:10 UTC: exact v1 request journal shows 403, request logs 0 rows,
user27 tasks and billing_operations 0 rows, quota/used_quota both zero. This is
no Gateway task/charge evidence, not a supplier-ledger audit or a known USD cost.

The v2 task is `task_4Yklp9dnD3eQcKosUVthynuw71MEi0rK`. **Resume it, never
submit another shape request merely because this checkout lacks ignored state.**
Source owner: Amp thread T-01a089aa-4a6b-711f-8eae-cde0a44d7d57. Its ignored
`assets/remaster/work/character-sarge-v2/` contains prototype, state, request and
response. Transfer these privately and verify their hashes before recovery.
Do not publish the journal, request data or private original Demo reference.

```sh
M=assets/remaster/characters/character-sarge-v2.json
uv run --with pillow==11.3.0 python assets/remaster/characters/produce.py resume --manifest "$M" --wait 1800
uv run --with pillow==11.3.0 python assets/remaster/characters/produce.py billing --manifest "$M"
uv run --with pillow==11.3.0 python assets/remaster/characters/produce.py receipt --manifest "$M"
```

`produce.py` imports the inspected Painter image and reuses the existing locked,
durably journaled production runner. It deliberately exposes no static MD3
processing. Receipt generation never grants runtime acceptance. Painter cost is
not exposed by the tool; unknown cost must not be converted to zero.

Targeted production-code checks (mock filesystem/renderer registration and
actual CPU tag implementation, **not the loader or a rendered match**):

```sh
cc -ffunction-sections -fdata-sections assets/remaster/characters/registration_test.c code/qcommon/q_shared.c -Wl,--gc-sections -lm -o /tmp/character-registration
/tmp/character-registration
cc -g -O1 -ffunction-sections -fdata-sections $(sdl2-config --cflags) assets/remaster/characters/tag_test.c code/qcommon/q_math.c -Wl,--gc-sections -lm -o /tmp/character-tag
/tmp/character-tag
RUN_BLENDER_TESTS=1 uv run --with pillow==11.3.0 python -m unittest discover -s misc/remaster-assets -p 'test_blender_iqm.py' -v
cmake --build build-orb --parallel 2
```

The tag regression exercises 25% interpolation on asymmetric translations,
negative/one-past-end/large indices in either argument, exact case and static
bind pose. Surface validation cannot protect `R_IQMLerpTag`: cgame queries tags
before scene submission. The implementation now applies the same frame-zero
fallback used by IQM surfaces instead of indexing beyond the pose allocation.
