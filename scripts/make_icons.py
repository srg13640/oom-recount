#!/usr/bin/env python3
"""Draw the app icon (plan line + observed fix) as PNGs and base64 text files, with no
third-party libraries. Run once; the output in site/icons/ is committed."""
import base64, math, pathlib, struct, zlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "site" / "icons"
GROUND, GRID, NAVY, GOLD = (243, 240, 231), (214, 210, 198), (47, 79, 162), (184, 138, 30)


def render(size, ss=3):
    S = size * ss
    k = S / 512
    px = bytearray(GROUND * S * S)
    def put(x, y, c):
        if 0 <= x < S and 0 <= y < S:
            i = 3 * (y * S + x); px[i:i + 3] = bytes(c)
    def rect(x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1)):
            for x in range(int(x0), int(x1)): put(x, y, c)
    def disk(cx, cy, r, c):
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r: put(x, y, c)
    def seg(x0, y0, x1, y1, w, c):  # thick line segment with round caps
        L = math.hypot(x1 - x0, y1 - y0)
        for t in range(int(L) + 1):
            disk(x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L, w / 2, c)
    for v in (150, 236, 322):
        rect(v * k - 2 * k, 96 * k, v * k + 2 * k, 416 * k, GRID); rect(96 * k, v * k - 2 * k, 416 * k, v * k + 2 * k, GRID)
    x0, y0, x1, y1 = 128 * k, 372 * k, 384 * k, 140 * k
    L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L
    t, dash, gap = 0, 46 * k, 26 * k
    while t < L:
        e = min(t + dash, L); seg(x0 + ux * t, y0 + uy * t, x0 + ux * e, y0 + uy * e, 26 * k, NAVY); t += dash + gap
    cx, cy, r = 300 * k, 170 * k, 40 * k
    rect(cx - 6 * k, cy - 74 * k, cx + 6 * k, cy + 74 * k, GOLD)
    for yy in (cy - 74 * k, cy + 74 * k): rect(cx - 22 * k, yy - 6 * k, cx + 22 * k, yy + 6 * k, GOLD)
    disk(cx, cy, r + 12 * k, GROUND); disk(cx, cy, r, GOLD)
    # downsample ss×ss
    out = bytearray()
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            acc = [0, 0, 0]
            for dy in range(ss):
                for dx in range(ss):
                    i = 3 * ((y * ss + dy) * S + x * ss + dx); acc[0] += px[i]; acc[1] += px[i + 1]; acc[2] += px[i + 2]
            row += bytes(v // (ss * ss) for v in acc)
        out += row
    def chunk(tag, data): return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(out), 9)) + chunk(b"IEND", b"")


OUT.mkdir(parents=True, exist_ok=True)
for s in (180, 192, 512):
    png = render(s)
    (OUT / f"icon{s}.png").write_bytes(png)
    (OUT / f"icon{s}.b64").write_text(base64.b64encode(png).decode())
    print(f"icon{s}.png {len(png):,} bytes")
