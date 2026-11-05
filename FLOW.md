# Google Flow clip generation (Veo 3.1 / Gemini Omni)

The target look comes from **Google Flow** (flow.google.com) — the free path using
the user's Flow credits. This replaces the Pillow placeholder renderer.

## Character consistency (the critical trick)

Use `character_ref.png` (single hero) or `character_sheet.png` (4 poses) as the
**LOCKED reference image** in EVERY clip. Same reference + same style line in every
prompt, so the hero stays identical across all clips.

Style line — append verbatim to every prompt:

> Stick figure with a large round WHITE head (filled), thick clean black outline,
> oval eyes, small mouth, thin black single-line limbs — no filled body. Flat white
> background, muted color accents only. Keep the character IDENTICAL to the reference image.

## Steps per scene

1. Open **flow.google.com** in the browser. Sign in with Google once (session persists).
2. Open the Create studio and pick the video model: **Veo 3.1** (highest quality, more
   credits) or **Gemini Omni** (faster/cheaper — start with Omni for the PoC).
3. Upload `character_ref.png` as the reference image.
4. Enter the narration line as the prompt, then append the style line above.
5. Generate a **5s, 16:9** clip. Download it.
6. Verify: hero consistent + correct? If not, regenerate once (max 1 retry).
7. Save to `clips/sceneNN.mp4`.

## Notes

- One clip per scene; per-scene narration voiceover already exists (Cloud TTS Algieba).
- The hero must look IDENTICAL across all clips — same reference + style line, always.
- If the model drifts (e.g. skin-colored head), the fix is the reference + the
  "head is pure paper-white" phrasing in the prompt.
