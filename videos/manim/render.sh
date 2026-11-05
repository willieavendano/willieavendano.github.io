#!/bin/bash
# render.sh — render a scene on the Mac Mini (lunalabmini) and pull the results back.
#
#   ./render.sh <scene_file.py> <SceneClass> [draft|final|say]
#
#   draft  (default) 720p15, silent, beat lengths estimated. ~1 min. Free.
#   final  1080p60 with ElevenLabs narration, loudness-normalized, plus captions.
#   say    720p15 with the macOS backup voice — a free way to hear the pacing.
#
# Results land in videos/manim/out/<SceneClass>/:
#   <SceneClass>.mp4            the render (final mode: <VIDEO_CODE>.mp4 + .srt)
#   sheet_NN.jpg                contact sheets, 3x3 tiles, one frame every 3 s
#                               (tile k of sheet n is at t = ((n-1)*9 + k-1) * 3 s)
#
# Manim, ffmpeg, the site fonts and the ElevenLabs key all live on the Mini;
# this machine only needs ssh + rsync. The key never leaves the Mini.
set -euo pipefail

FILE="${1:?usage: render.sh <scene_file.py> <SceneClass> [draft|final|say]}"
SCENE="${2:?usage: render.sh <scene_file.py> <SceneClass> [draft|final|say]}"
MODE="${3:-draft}"

HERE="$(cd "$(dirname "$0")" && pwd)"
MINI="${MINI_HOST:-luna@100.121.78.28}"
REMOTE="render/phy-videos"
STEM="${FILE%.py}"

case "$MODE" in
  draft) FLAGS="-r 1280,720 --fps 15"; QDIR="720p15";  NARR=draft ;;
  say)   FLAGS="-r 1280,720 --fps 15"; QDIR="720p15";  NARR=say ;;
  final) FLAGS="-qh --disable_caching"; QDIR="1080p60"; NARR=eleven ;;  # caching drops narration audio on partially cached scenes
  *) echo "mode must be draft, final or say" >&2; exit 2 ;;
esac

# One render at a time: concurrent manim runs share media/texts/ on the Mini and
# race on the SVG text cache (FileNotFoundError …/media/texts/<hash>_.svg).
# The lock is a directory so it works without flock; a stale one after a hard
# kill is removed by hand (rmdir videos/manim/.render.lock).
LOCK="$HERE/.render.lock"
until mkdir "$LOCK" 2>/dev/null; do sleep 5; done
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

ssh -o BatchMode=yes "$MINI" "mkdir -p $REMOTE"
rsync -a --exclude media --exclude out --exclude __pycache__ --exclude .DS_Store \
  "$HERE/" "$MINI:$REMOTE/"

# shellcheck disable=SC2087
ssh -o BatchMode=yes "$MINI" /bin/bash -s <<EOF
set -euo pipefail
export PATH="\$HOME/.local/bin:/opt/homebrew/bin:\$PATH"
cd "\$HOME/$REMOTE"
export NARRATION=$NARR
if [ "$NARR" = eleven ]; then
  export ELEVENLABS_API_KEY="\$(grep -E '^ELEVENLABS_API_KEY=' "\$HOME/.hermes/.env" | cut -d= -f2-)"
  if [ -f voice.env ]; then set -a; . ./voice.env; set +a; fi
fi

# Everything below reads this script from stdin, so no child may touch stdin.
manim $FLAGS --progress_bar none -v WARNING "$FILE" "$SCENE" < /dev/null

SRC="media/videos/$STEM/$QDIR/$SCENE.mp4"
OUT="out/$SCENE"
rm -rf "\$OUT"; mkdir -p "\$OUT"
if [ "$MODE" = final ]; then
  CODE="\$(python3 - "$FILE" "$SCENE" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
body = src.split("class " + sys.argv[2], 1)[1]
print(re.search(r'VIDEO_CODE\s*=\s*"([^"]+)"', body).group(1))
PY
)"
  # One consistent loudness across the whole library (YouTube targets -14 LUFS).
  ffmpeg -nostdin -y -loglevel error -i "\$SRC" -c:v copy \
    -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a aac -b:a 192k -movflags +faststart "\$OUT/\$CODE.mp4"
  cp "captions/\$CODE.srt" "\$OUT/" 2>/dev/null || true
  VIDEO="\$OUT/\$CODE.mp4"
else
  cp "\$SRC" "\$OUT/$SCENE.mp4"
  VIDEO="\$OUT/$SCENE.mp4"
fi
ffmpeg -nostdin -y -loglevel error -i "\$VIDEO" -vf "fps=1/3,scale=640:-2,tile=3x3" -q:v 3 "\$OUT/sheet_%02d.jpg"
printf 'duration: %ss\n' "\$(ffprobe -v error -show_entries format=duration -of csv=p=0 "\$VIDEO")"
EOF

mkdir -p "$HERE/out/$SCENE"
rsync -a --delete "$MINI:$REMOTE/out/$SCENE/" "$HERE/out/$SCENE/"
rsync -a "$MINI:$REMOTE/narration_cache/" "$HERE/narration_cache/" 2>/dev/null || true
rsync -a "$MINI:$REMOTE/captions/" "$HERE/captions/" 2>/dev/null || true
echo "results: $HERE/out/$SCENE/"
ls "$HERE/out/$SCENE/"
