#!/usr/bin/env python3
"""New video project: topic -> DeepSeek script -> <repo>/<slug>/script.json

Modes:
  create_project.py --topic "What if ...?"                              # new project
  create_project.py --topic "..." --project <id> --feedback "..."        # revise existing
"""
import json, os, re, sys, argparse, urllib.request, urllib.error

OUT = "/opt/data/workspace/stickfigure-director"

SYS_PROMPT = """You write YouTube "What If" video scripts starring TimTom, a recurring photorealistic adult man.
A calm off-screen narrator tells the story; TimTom never speaks — he appears in the visuals and lives through the scenario.

Output STRICT JSON only (no markdown, no prose). Schema:
{
  "title": "What If ...?",
  "topic": "one short paragraph (2-3 sentences) summarizing the scenario and its emotional stakes",
  "language": "en",
  "scenes": [
    {"id": 1, "chapter": "Hook", "duration_seconds": 6,
     "narration": "one warm spoken English sentence (8-18 words)",
     "visual": "photorealistic cinematic description: one clear subject + action + setting, TimTom present",
     "timtom_mode": "beides", "beat": "hook"}
  ]
}

Rules:
- 40 to 50 scenes.
- duration_seconds: only 4, 6, 8, or 10.
- Narrative arc, beats in order: hook (1 scene), premise (2-3), exploration (the bulk, ~30, grouped into numbered chapters), escalation (3-5), resolution (2-3).
- chapter labels: "Hook", "Prämisse", "Kapitel 1: <name>", "Kapitel 2: <name>", ..., "Eskalation: <name>", "Auflösung: <name>".
- timtom_mode: "beides" (narrator + TimTom shown), "erlebt" (TimTom actively living it, camera on him), "erzählt" (narrator explains, TimTom optional).
- Each "visual": photorealistic, specific, one subject + action + setting; no text overlays, no captions. TimTom is the consistent protagonist.
- "narration" is for a voiceover: warm, natural, one idea per sentence, no lists, no emojis, no quotes.
- Story is self-contained with rising stakes, a climax, and a satisfying payoff."""


def load_env():
    env = dict(os.environ)
    p = "/opt/data/.env"
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k, v)
    return env


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "project"


def call_deepseek(topic, env, feedback="", existing=None, direction=""):
    url = env["DEEPSEEK_BASE_URL"].rstrip("/") + "/chat/completions"
    user = f"Topic: {topic}"
    if direction:
        user += f"\n\nStory direction / requested content (follow this): {direction}"
    if feedback:
        user += f"\n\nRevision instructions (follow exactly): {feedback}"
    if existing:
        user += ("\n\nCurrent script to revise (keep what works, change only what the "
                 "instructions ask):\n" + json.dumps(existing, ensure_ascii=False))
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.9,
        "response_format": {"type": "json_object"},
        "max_tokens": 8192,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {env['DEEPSEEK_API_KEY']}"})
    resp = json.loads(urllib.request.urlopen(req, timeout=180).read())
    choice = resp["choices"][0]
    if choice.get("finish_reason") == "length":
        print("WARNING: response truncated (length) — script may be incomplete", file=sys.stderr)
    return json.loads(choice["message"]["content"])


def validate(script):
    assert isinstance(script, dict), "script must be an object"
    assert "title" in script and "scenes" in script, "missing title/scenes"
    script.setdefault("language", "en")
    script.setdefault("topic", "")
    sc = script["scenes"]
    assert isinstance(sc, list) and 20 <= len(sc) <= 60, f"scene count out of range: {len(sc)}"
    valid_modes = {"beides", "erlebt", "erzählt"}
    valid_beats = {"hook", "premise", "exploration", "escalation", "resolution"}
    for i, s in enumerate(sc):
        s["id"] = i + 1
        assert s.get("narration"), f"scene {i+1} missing narration"
        assert s.get("visual"), f"scene {i+1} missing visual"
        d = s.get("duration_seconds")
        if d not in (4, 6, 8, 10):
            s["duration_seconds"] = 8 if d is None else max(4, min(10, round(d / 2) * 2))
        if s.get("timtom_mode") not in valid_modes:
            s["timtom_mode"] = "beides"
        if s.get("beat") not in valid_beats:
            s["beat"] = "exploration"
        s.setdefault("chapter", "")
    return script


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--project", help="existing project id to update (omit to create new)")
    ap.add_argument("--feedback", default="", help="revision instructions for an existing project")
    args = ap.parse_args()

    env = load_env()
    existing = None
    if args.project:
        d = os.path.join(OUT, args.project)
        if not os.path.isfile(os.path.join(d, "script.json")):
            print(f"project '{args.project}' not found", file=sys.stderr)
            sys.exit(1)
        existing = json.load(open(os.path.join(d, "script.json")))

    print("generating script ...")
    script = call_deepseek(args.topic, env, args.feedback, existing)
    script = validate(script)
    print(f"  title={script['title']!r}, {len(script['scenes'])} scenes")

    if args.project:
        pid, d = args.project, os.path.join(OUT, args.project)
    else:
        pid = slugify(script["title"])[:60]
        d = os.path.join(OUT, pid)
        n = 2
        while os.path.exists(d):
            pid = f"{slugify(script['title'])[:52]}-{n}"
            d = os.path.join(OUT, pid)
            n += 1
        os.makedirs(d)

    path = os.path.join(d, "script.json")
    json.dump(script, open(path, "w"), indent=2, ensure_ascii=False)
    print(f"  wrote {path}")
    print(f"PROJECT_ID={pid}")


if __name__ == "__main__":
    main()
