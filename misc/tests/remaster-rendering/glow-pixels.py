"""Check lossless, matched-camera glow-control captures (requires ImageMagick)."""
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
for hdr in (0, 1):
    for view in ("visible", "blocked"):
        def region(variant):
            return subprocess.check_output([
                "magick", str(root / f"{view}-{variant}-hdr{hdr}.png"),
                "-gravity", "center", "-crop", "200x200+0+0", "+repage",
                "-depth", "8", "rgb:-",
            ])

        on, off = region("on"), region("off")
        assert len(on) == len(off) == 200 * 200 * 3
        delta = [abs(a - b) for a, b in zip(on, off)]
        pixels = sum(any(delta[i:i + 3]) for i in range(0, len(delta), 3))
        peak = max(delta)
        if view == "visible":
            assert pixels > 100 and peak > 10, "positive glow control must be visible"
        else:
            assert pixels == 0, "glow must not leak through foreground world geometry"
        print(f"PASS HDR{hdr} {view}: changed pixels={pixels}, peak channel delta={peak}")
        if view == "blocked":
            wrong = region("leak")
            delta = [abs(a - b) for a, b in zip(wrong, off)]
            pixels = sum(any(delta[i:i + 3]) for i in range(0, len(delta), 3))
            assert pixels > 100 and max(delta) > 10, "depth bypass must expose the glow, not a PVS-hidden model"
            print(f"PASS HDR{hdr} deliberately broken depth: {pixels} leaking pixels, peak={max(delta)}")
