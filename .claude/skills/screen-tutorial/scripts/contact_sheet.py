"""Contact sheets for a finished tutorial MP4 — without ffmpeg.

Mirrors the Manim pipeline's `sheet_NN.jpg` review aid (videos/manim/README.md
§ 2): 3x3 tiles, one frame every N seconds, each stamped with its time, so
the layout can be checked without scrubbing through the video.

There is no ffmpeg on the school Macs, so frames come from AVFoundation
(`AVAssetImageGenerator`) through a ~70-line Swift helper embedded below. It is
compiled once with `swiftc` (part of the Xcode Command Line Tools) and cached
in the temp directory. On a Mac without `swiftc` the sheets are skipped with a
warning: they are a review aid, not a deliverable.

    python3 contact_sheet.py out/DEMO/DEMO.mp4 [--every 3] [--out DIR]
    python3 contact_sheet.py out/DEMO/DEMO.mp4 --at 12.5 --at 14 --frames-only
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SWIFT_SOURCE = r'''
import AVFoundation
import AppKit

// usage: frames <video> <out_prefix> <cols> <rows> <tile_width> <t1> <t2> ...
//   writes <out_prefix>01.jpg, 02.jpg ... (cols x rows tiles per sheet)
//   cols = rows = 1 writes one JPEG per time. Prints "duration=<s>" first.
let a = CommandLine.arguments
if a.count < 6 { FileHandle.standardError.write("bad args\n".data(using: .utf8)!); exit(2) }
let asset = AVURLAsset(url: URL(fileURLWithPath: a[1]))
let prefix = a[2]
let cols = Int(a[3])!, rows = Int(a[4])!, tileW = CGFloat(Double(a[5])!)
let times = a.dropFirst(6).map { Double($0)! }
print("duration=\(CMTimeGetSeconds(asset.duration))")

let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.requestedTimeToleranceBefore = CMTime(value: 1, timescale: 60)
gen.requestedTimeToleranceAfter = CMTime(value: 1, timescale: 60)

func grab(_ t: Double) -> CGImage? {
    return try? gen.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil)
}

func save(_ rep: NSBitmapImageRep, _ path: String) {
    let data = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.82])!
    try! data.write(to: URL(fileURLWithPath: path))
}

let perSheet = cols * rows
var sheet = 0
var i = 0
while i < times.count {
    let chunk = Array(times[i..<min(i + perSheet, times.count)])
    var tileH: CGFloat = tileW * 9 / 16
    if let first = grab(chunk[0]) { tileH = tileW * CGFloat(first.height) / CGFloat(first.width) }
    let gap: CGFloat = cols * rows == 1 ? 0 : 6
    let W = Int(CGFloat(cols) * tileW + CGFloat(cols + 1) * gap)
    let H = Int(CGFloat(rows) * tileH + CGFloat(rows + 1) * gap)
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: W, pixelsHigh: H,
                               bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let ctx = NSGraphicsContext.current!.cgContext
    ctx.setFillColor(NSColor(white: 0.12, alpha: 1).cgColor)
    ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
    for (k, t) in chunk.enumerated() {
        let c = k % cols, r = k / cols
        let x = gap + CGFloat(c) * (tileW + gap)
        let y = CGFloat(H) - gap - CGFloat(r + 1) * tileH - CGFloat(r) * gap
        if let img = grab(t) { ctx.draw(img, in: CGRect(x: x, y: y, width: tileW, height: tileH)) }
        if cols * rows > 1 {
            let label = String(format: " %d:%04.1f ", Int(t) / 60, t.truncatingRemainder(dividingBy: 60))
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.monospacedDigitSystemFont(ofSize: 15, weight: .bold),
                .foregroundColor: NSColor.white, .backgroundColor: NSColor(white: 0, alpha: 0.7)]
            NSAttributedString(string: label, attributes: attrs).draw(at: NSPoint(x: x + 6, y: y + 6))
        }
    }
    NSGraphicsContext.restoreGraphicsState()
    sheet += 1
    save(rep, prefix + String(format: "%02d.jpg", sheet))
    i += perSheet
}
'''


def _helper():
    """Path to the compiled frame helper, building it on first use. None if
    this Mac has no Swift compiler."""
    digest = hashlib.sha1(SWIFT_SOURCE.encode()).hexdigest()[:12]
    folder = Path(tempfile.gettempdir()) / "screen-tutorial"
    binary = folder / ("frames-" + digest)
    if binary.exists():
        return binary
    swiftc = shutil.which("swiftc")
    if not swiftc:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    src = folder / ("frames-" + digest + ".swift")
    src.write_text(SWIFT_SOURCE)
    proc = subprocess.run([swiftc, "-O", "-o", str(binary), str(src)],
                          capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        sys.stderr.write("contact_sheet: swiftc failed:\n" + proc.stderr[-1500:] + "\n")
        return None
    return binary


def _run(video, prefix, cols, rows, tile_width, times):
    helper = _helper()
    if helper is None:
        return None
    proc = subprocess.run([str(helper), str(video), str(prefix), str(cols), str(rows),
                           str(tile_width)] + ["%.3f" % t for t in times],
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError("frame helper failed: " + proc.stderr[-800:])
    for line in proc.stdout.splitlines():
        if line.startswith("duration="):
            return float(line.split("=", 1)[1])
    return 0.0


def video_duration(video):
    """Duration of an MP4 in seconds (None if the helper is unavailable)."""
    with tempfile.TemporaryDirectory() as tmp:
        return _run(video, Path(tmp) / "d", 1, 1, 64, [0.0])


def make_sheets(video, out_dir, every=3.0, cols=3, rows=3, tile_width=480, duration=None):
    """Write sheet_01.jpg, sheet_02.jpg ... into out_dir. Returns the paths
    (empty list, with a warning on stderr, if frames cannot be extracted)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("sheet_*.jpg"):
        old.unlink()
    if duration is None:
        duration = video_duration(video)
    if duration is None:
        sys.stderr.write("contact_sheet: no swiftc on this Mac; skipping contact sheets "
                         "(install the Xcode Command Line Tools to enable them)\n")
        return []
    times = []
    t = min(0.5, duration / 2)
    while t < duration - 0.05:
        times.append(t)
        t += every
    if not times:
        return []
    _run(video, out_dir / "sheet_", cols, rows, tile_width, times)
    return sorted(out_dir.glob("sheet_*.jpg"))


def grab_frames(video, times, out_dir, width=960):
    """One JPEG per requested time: frame_01.jpg ... (for sync spot checks)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, t in enumerate(times, start=1):
        prefix = out_dir / ("frame_%02d_" % i)
        if _run(video, prefix, 1, 1, width, [t]) is None:
            return []
        produced = Path(str(prefix) + "01.jpg")
        final = out_dir / ("frame_%02d_%05.1fs.jpg" % (i, t))
        produced.replace(final)
        paths.append(final)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description="3x3 contact sheets (or single frames) from an MP4.")
    ap.add_argument("video")
    ap.add_argument("--every", type=float, default=3.0, help="seconds between tiles (default 3)")
    ap.add_argument("--out", help="output folder (default: next to the video)")
    ap.add_argument("--at", type=float, action="append", help="grab single frames at these times")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else Path(args.video).parent
    if args.at:
        for p in grab_frames(args.video, args.at, out):
            print(p)
    else:
        for p in make_sheets(args.video, out, every=args.every):
            print(p)


if __name__ == "__main__":
    main()
