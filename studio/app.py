import os, re, json, shutil, subprocess, sys, uuid, time
from flask import Flask, jsonify, request, send_file, abort, Response

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("PROJECTS_ROOT", "/opt/data/workspace/stickfigure-director")
REGISTRY = os.path.join(ROOT, ".studio.json")
QUEUE = os.path.join(ROOT, "queue.json")

app = Flask(__name__, static_folder=os.path.join(APP_DIR, "static"), static_url_path="")

STUDIO_USERNAME = os.environ.get("STUDIO_USERNAME", "matthias")
STUDIO_PASSWORD = os.environ.get("STUDIO_PASSWORD", "")


@app.before_request
def _require_auth():
    if not STUDIO_PASSWORD:
        return  # no password configured -> open (dev mode)
    auth = request.authorization
    if not auth or auth.username != STUDIO_USERNAME or auth.password != STUDIO_PASSWORD:
        return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="studio"'})


def load_registry():
    if os.path.exists(REGISTRY):
        try:
            return json.load(open(REGISTRY))
        except Exception:
            return {}
    return {}


def save_registry(reg):
    json.dump(reg, open(REGISTRY, "w"), indent=2, ensure_ascii=False)


def load_queue():
    if os.path.exists(QUEUE):
        try:
            q = json.load(open(QUEUE))
            if isinstance(q, dict) and isinstance(q.get("queue"), list):
                return q
        except Exception:
            pass
    return {"queue": []}


def save_queue(q):
    json.dump(q, open(QUEUE, "w"), indent=2, ensure_ascii=False)


def pdir(pid):
    d = os.path.join(ROOT, pid)
    if os.path.isdir(d) and os.path.isfile(os.path.join(d, "script.json")):
        return d
    return None


def newest(d, pred):
    hits = [f for f in os.listdir(d) if pred(f)]
    if not hits:
        return None
    return os.path.join(d, max(hits, key=lambda f: os.path.getmtime(os.path.join(d, f))))


def find_master(d):
    return newest(d, lambda f: f.endswith("_1080p.mp4"))


def find_preview(d):
    p = os.path.join(d, "preview_720p.mp4")
    return p if os.path.isfile(p) else newest(d, lambda f: f.startswith("preview_720p") and f.endswith(".mp4"))


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "project"


def project_progress(pid):
    d = pdir(pid)
    if not d:
        return None
    script = json.load(open(os.path.join(d, "script.json")))
    cdir = os.path.join(d, "clips")
    nclips = len([f for f in os.listdir(cdir) if f.endswith(".mp4")]) if os.path.isdir(cdir) else 0
    return {
        "scene_count": len(script.get("scenes", [])),
        "clips": nclips,
        "has_master": find_master(d) is not None,
        "has_preview": find_preview(d) is not None,
    }


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/projects")
def api_projects():
    reg = load_registry()
    out = []
    for name in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, name)
        if not (os.path.isdir(d) and os.path.isfile(os.path.join(d, "script.json"))):
            continue
        script = json.load(open(os.path.join(d, "script.json")))
        meta = reg.get(name, {})
        master = find_master(d)
        preview = find_preview(d)
        cdir = os.path.join(d, "clips")
        nclips = len([f for f in os.listdir(cdir) if f.endswith(".mp4")]) if os.path.isdir(cdir) else 0
        out.append({
            "id": name,
            "title": script.get("title", name),
            "scene_count": len(script.get("scenes", [])),
            "confirmed": bool(meta.get("confirmed")),
            "has_master": master is not None,
            "has_preview": preview is not None,
            "clips": nclips,
            "master_size": os.path.getsize(master) if master else 0,
            "preview_size": os.path.getsize(preview) if preview else 0,
        })
    return jsonify(out)


@app.route("/api/projects/<pid>")
def api_project(pid):
    d = pdir(pid)
    if not d:
        abort(404)
    return jsonify(json.load(open(os.path.join(d, "script.json"))))


@app.route("/api/projects/<pid>/script", methods=["PUT"])
def api_save_script(pid):
    d = pdir(pid)
    if not d:
        abort(404)
    data = request.get_json(force=True)
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        abort(400, "bad shape")
    json.dump(data, open(os.path.join(d, "script.json"), "w"), indent=2, ensure_ascii=False)
    return jsonify({"ok": True})


@app.route("/api/projects/<pid>/preview")
def api_preview(pid):
    d = pdir(pid)
    if not d:
        abort(404)
    p = find_preview(d)
    if not p:
        abort(404)
    return send_file(p, mimetype="video/mp4", conditional=True)


@app.route("/api/projects/<pid>/master")
def api_master(pid):
    d = pdir(pid)
    if not d:
        abort(404)
    p = find_master(d)
    if not p:
        abort(404)
    return send_file(p, as_attachment=True, download_name=os.path.basename(p),
                     mimetype="video/mp4", conditional=True)


@app.route("/api/projects/<pid>/confirm", methods=["POST"])
def api_confirm(pid):
    d = pdir(pid)
    if not d:
        abort(404)
    reg = load_registry()
    reg.setdefault(pid, {})["confirmed"] = True
    save_registry(reg)
    subprocess.Popen([sys.executable, os.path.join(APP_DIR, "cleanup.py"), pid],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({"ok": True, "confirmed": True})


@app.route("/api/projects", methods=["POST"])
def api_create():
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    if not title:
        abort(400, "title required")
    pid = slugify(title)
    d = os.path.join(ROOT, pid)
    if os.path.exists(d):
        abort(409, "project exists")
    os.makedirs(d)
    script = {"title": title, "topic": data.get("topic", "").strip(), "language": "en", "scenes": []}
    json.dump(script, open(os.path.join(d, "script.json"), "w"), indent=2, ensure_ascii=False)
    return jsonify({"ok": True, "id": pid})


@app.route("/api/queue")
def api_queue():
    q = load_queue()
    for e in q["queue"]:
        e["progress"] = project_progress(e.get("project_id")) if e.get("project_id") else None
    return jsonify(q)


@app.route("/api/queue", methods=["POST"])
def api_queue_add():
    data = request.get_json(force=True)
    topic = (data.get("topic") or "").strip()
    if not topic:
        abort(400, "topic required")
    notes = (data.get("notes") or "").strip()
    q = load_queue()
    entry = {
        "id": uuid.uuid4().hex[:8],
        "topic": topic,
        "notes": notes,
        "status": "pending",
        "project_id": None,
        "created_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "updated_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    }
    q["queue"].append(entry)
    save_queue(q)
    return jsonify({"ok": True, "entry": entry})


@app.route("/api/queue/<qid>", methods=["DELETE"])
def api_queue_remove(qid):
    q = load_queue()
    q["queue"] = [e for e in q["queue"] if e["id"] != qid]
    save_queue(q)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), threaded=True)
