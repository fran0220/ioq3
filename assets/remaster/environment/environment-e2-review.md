# E2 standing lantern candidate, 2026-09-11

`environment-scene-q3dm1-v1.pk3` contains the accepted front-facing crest
binding and four new opaque standing-lantern instances. SHA-256:
`8620cb647422f273950340803a988eb4b224d034a0bcd767e829d28aba427cc6`.
No BSP, AAS or reference imagery is embedded. Source receipts retain the two
unique Hunyuan jobs, each billed $0.50; Painter cost remains undisclosed.

Actual observer-enabled WASM loaded all five bindings, including surfaces
2063/2065/2067/2069. Both HDR1 and HDR0 reached state8 with contextLost=false.
Startup camera `noclip; setviewpos 674 1460 40 90` settled at
`[674,1475.50134,41]`, angles `[0,90,0]`. No exposure/material compensation.
Inspected captures: `.amp/in/artifacts/environment-e2/{hdr,ldr}-review.jpg`.
Two lanterns are visible, ivory/graphite forms readable, but the left fixture
is partly cropped, details remain weak and bright structural panels dominate.
This is a fixed-view candidate check, not four-location acceptance or Bot/PVS
regression. Original flame surfaces still exist in v1 even where not visible
in these captures; next atomic-group revision must suppress them with the
corresponding solid sources. No original content is credited as a remake.

`build_scene.py` verified independent asymmetric fit:
source `[-1,-2,0,3,4,8]`, target `[[10,20,30],[30,50,70]]`, margin .8
produces origin `[16,31,34]`, scale4, bounds `[[12,23,34],[28,47,66]]`.
Margins0/1/-1 are rejected. All four exported bounds fit strictly inside
their measured original solid envelopes.

Per-surface ledger records 2097 source surfaces, five bound candidates and
2092 retained original geometries. Full-map and final-art acceptance remain
false. E3 wall-lantern mesh/export completed, not yet runtime accepted.
Character statue source transferred and archive hash independently matched
`d38908d61475806cb720a45a8a6f20c56ac2842ec98307a6c870f1e5b10b62ed`;
no statue derivative or character acceptance is claimed.
