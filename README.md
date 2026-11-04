# stickfigure-director

End-to-end stick-figure explainer video pipeline (PoC).

## What it does

```
topic -> DeepSeek (story/scenes JSON) -> Google Cloud TTS Chirp3 "Algieba" (voiceover)
      -> Pillow character render (placeholder visuals) -> ffmpeg -> MP4
```

## Setup (inside the Hermes agent container, as root)

```bash
./setup.sh
```

## Run

```bash
.venv/bin/python pipeline.py "Why do we procrastinate?"
# -> writes pipeline_demo.mp4
```

## Env vars (already set in the container)

- `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL` (story LLM)
- `GOOGLE_API_KEY` (Cloud TTS)
- `VOICE_NAME` (default `en-US-Chirp3-HD-Algieba`)

Keys are read from the container environment first, then `/opt/data/.env` as fallback.

## Design notes

- **Visuals are a placeholder.** The Pillow renderer (`character.py`) is deterministic
  and free. The target look — hand-drawn, thick outlines, expressive face — comes from
  **Google Flow** clips (Veo 3.1 / Gemini Omni Flash) driven via browser automation of
  labs.google/fx, using a **locked character sheet** pasted into every clip prompt for
  consistency. Wire Flow in as the next phase.
- **Voice** = Google Cloud TTS Chirp3 HD (human-sounding). The Gemini API
  (`generativelanguage.googleapis.com`) is blocked by the org policy; Cloud TTS
  (`texttospeech.googleapis.com`) works with a plain API key and uses the same voices.
- **Story LLM** = DeepSeek (Gemini API blocked, see above).
- **Character** = a named pose/expression library (`POSES`, `EXPRESSIONS`) so every
  scene reuses the exact same hero.
