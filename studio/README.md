# Studio — Deployment-Anleitung (Coolify)

Kleines Web-UI zur Verwaltung der „What If"-Video-Pipeline:
Projektliste, Skript-Editor (Szenen/Narration/Visual), Vorschau, Original-Download,
und „als fertig bestätigen" (löst Bereinigung der Zwischendateien aus).

## Coolify-Einrichtung

1. **Neue App (Application)** anlegen, Source = das Repo/Verzeichnis mit diesem `studio/`-Ordner.
2. **Build Pack:** `Dockerfile`
   - **Base Directory / Build Context:** `studio/`
   - **Dockerfile location:** `Dockerfile` (liegt in `studio/`)
3. **Port:** `8080` (Exposed Port)
4. **Volume mount** (wichtig — hier liegen alle Projektdaten):
   - Host: `/opt/data/workspace/stickfigure-director`
   - Container: `/data`
   - Typ: Bind-Mount
5. **Environment-Variable:**
   - `PROJECTS_ROOT=/data`

Die App ist **stateless**: alle Daten (Skripte, Videos, `.studio.json`) liegen im
gemounteten Volume. Ein Redeploy verliert nichts.

## Alternative: docker compose (ohne Coolify)

```bash
cd studio
docker compose up -d --build
```

(Gleiche Wirkung wie oben: Port 8080, Volume `/opt/data/workspace/stickfigure-director` → `/data`.)

## ⚠️ Sicherheit

Die App hat **keine Authentifizierung**. Jeder mit Zugriff auf den Port kann
Skripte bearbeiten, Videos laden und die Bereinigung auslösen. Mindestens eine
der Maßnahmen aktivieren:

- Coolify-eigene **Basic Auth** für die Domain aktivieren, ODER
- Zugriff nur über VPN / interne IP, ODER
- Reverse-Proxy mit Auth davor.

## Datenmodell

- Ein Projekt = ein Unterordner in `PROJECTS_ROOT`, der eine `script.json` enthält.
- `script.json`: `{ title, topic, language, scenes: [{ id, chapter, duration_seconds, narration, visual, timtom_mode, beat }] }`.
- Master-Video: `<name>_1080p.mp4` · Vorschau: `preview_720p.mp4`.
- Bereinigung löscht: `clips/`, `work/`, `clips_v3_prelim/`, `voice_test/`, `vo_cont/`, alte `*_v1*`/`*noflare*`-MP4s. Behalten: Master, Vorschau, `script.json`, `manifest.json`, Pipeline-Skripte.
