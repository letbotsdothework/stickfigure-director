"""End-to-end stick-figure video pipeline (PoC v2).

topic -> DeepSeek (story/scenes JSON) -> Cloud TTS Chirp3 "Charon" (voiceover)
     -> Pillow character render (placeholder visuals) -> ffmpeg -> MP4

The Pillow renderer is a STAND-IN until Google Flow clips are wired in
(browser automation of labs.google/fx). Per-scene audio matches the final
architecture (one Flow clip + one voiceover line per scene).
"""
import json
import os
import sys
import math
import subprocess
import urllib.request
import urllib.error
import base64

from PIL import Image, ImageDraw
from character import draw_character, load_font, text_center, W, H, FPS, BG, INK, MUTED

OUT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(OUT, "pipeline_run")


def load_env():
    env = dict(os.environ)                      # container env vars (agent)
    p = "/opt/data/.env"                        # local fallback (this host)
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k, v)
    return env


# ---------------------------------------------------------------------------
# 1. Story generation (DeepSeek, OpenAI-compatible)
# ---------------------------------------------------------------------------
def gen_story(topic, env):
    url = env["DEEPSEEK_BASE_URL"].rstrip("/") + "/chat/completions"
    sys_prompt = (
        "You write short stick-figure explainer video scripts. Output STRICT JSON only, "
        "no markdown, no prose. Schema:\n"
        '{"title": "...", "segments": [{"narration": "one warm spoken sentence", '
        '"pose": "stand|point|think|celebrate|sad|run", '
        '"expr": "neutral|happy|surprised|worried|sad|confident", '
        '"caption": "short on-screen words (max 6 words)"}]}\n'
        "Rules: 5 segments, hook first, one idea per segment, warm + friendly tone, "
        "English, each narration 8-16 words."
    )
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        "temperature": 0.9,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {env['DEEPSEEK_API_KEY']}"})
    resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
    content = resp["choices"][0]["message"]["content"]
    return json.loads(content)


# ---------------------------------------------------------------------------
# 2. Voiceover (Cloud TTS Chirp3 "Charon")
# ---------------------------------------------------------------------------
def tts(text, out_path, env, voice=None):
    voice = voice or env.get("VOICE_NAME", "en-US-Chirp3-HD-Algieba")
    url = "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + env["GOOGLE_API_KEY"]
    body = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": voice},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
    open(out_path, "wb").write(base64.b64decode(resp["audioContent"]))
    return out_path


def audio_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(out.stdout.strip())


# ---------------------------------------------------------------------------
# 3. Visual rendering (Pillow placeholder for Flow clips)
# ---------------------------------------------------------------------------
def draw_caption(d, text):
    font = load_font(40, bold=True)
    # word-wrap to ~44 chars
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 44:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    y = H - 90
    for ln in reversed(lines):
        text_center(d, (W / 2, y), ln, font, fill=(40, 40, 46))
        y -= 48


def render_scene(seg, idx, total, dur, out_dir):
    """One scene: title/character + caption, duration matched to its audio."""
    frames = os.path.join(out_dir, f"scene{idx}")
    os.makedirs(frames, exist_ok=True)
    pose = seg.get("pose", "stand")
    expr = seg.get("expr", "neutral")
    cap = seg.get("caption", "")
    narration = seg.get("narration", "")
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        # gentle bob
        bob = 4 * math.sin(t * 2.2)
        draw_character(d, W / 2, H - 100 + bob, s=1.8, pose=pose, expr=expr,
                       walk_phase=0.5 if pose == "run" else 0.0)
        draw_caption(d, cap)
        img.save(os.path.join(frames, f"{i:05d}.png"))
    return frames


def render_title(title, dur, out_dir):
    frames = os.path.join(out_dir, "scene_title")
    os.makedirs(frames, exist_ok=True)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        big = load_font(58, bold=True)
        # wrap title
        words = title.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 20:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        y = H / 2 - 60
        for ln in lines:
            text_center(d, (W / 2, y), ln, big)
            y += 70
        draw_character(d, W / 2, H - 60, s=1.7, pose="think", expr="worried")
        img.save(os.path.join(frames, f"{i:05d}.png"))
    return frames


# ---------------------------------------------------------------------------
# 4. Assemble (ffmpeg concat + audio mux)
# ---------------------------------------------------------------------------
def assemble(parts, out_mp4):
    """parts = list of (frames_dir, audio_mp3)."""
    with open(os.path.join(WORK, "concat.txt"), "w") as f:
        for frames, audio in parts:
            subprocess.run(
                ["ffmpeg", "-y", "-framerate", str(FPS), "-i",
                 os.path.join(frames, "%05d.png"), "-i", audio,
                 "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                 "-pix_fmt", "yuv420p", "-preset", "fast", "-c:a", "aac",
                 "-shortest", f"{frames}.mp4"],
                capture_output=True)
            f.write(f"file '{os.path.abspath(frames)}.mp4'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
         os.path.join(WORK, "concat.txt"), "-c", "copy", out_mp4],
        capture_output=True)
    return out_mp4


def main(topic):
    env = load_env()
    os.makedirs(WORK, exist_ok=True)
    print("1) story ...")
    story = gen_story(topic, env)
    title = story["title"]
    segs = story["segments"]
    print(f"   title={title!r}, {len(segs)} segments")

    # title audio (speak the title) + per-segment audio
    parts = []
    ttl_mp3 = os.path.join(WORK, "ttl.mp3")
    tts(title, env=env, out_path=ttl_mp3)
    ttl_dur = audio_duration(ttl_mp3) + 0.6
    parts.append((render_title(title, ttl_dur, WORK), ttl_mp3))

    for i, seg in enumerate(segs):
        mp3 = os.path.join(WORK, f"seg{i}.mp3")
        tts(seg["narration"], mp3, env)
        dur = audio_duration(mp3) + 0.5
        parts.append((render_scene(seg, i, len(segs), dur, WORK), mp3))

    print("2) assembling ...")
    out = os.path.join(OUT, "pipeline_demo.mp4")
    assemble(parts, out)
    d = audio_duration(out)
    print(f"3) done: {out} ({d:.1f}s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Why do we procrastinate?")
