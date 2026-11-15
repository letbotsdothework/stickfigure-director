#!/usr/bin/env python3
"""Queue processor: takes the next pending topic, generates its script via DeepSeek,
creates the project folder, and marks the queue entry 'scripted'.

Usage: python3 process_queue.py [--all]
       (default: only the FIRST pending entry; --all processes every pending entry)
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from create_project import load_env, call_deepseek, validate, slugify

ROOT = "/opt/data/workspace/stickfigure-director"
QUEUE = os.path.join(ROOT, "queue.json")


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


def process_one(entry, env):
    topic = entry["topic"]
    print(f"topic: {topic}")
    script = validate(call_deepseek(topic, env))
    pid = slugify(script["title"])[:60]
    d = os.path.join(ROOT, pid)
    n = 2
    while os.path.exists(d):
        pid = f"{slugify(script['title'])[:52]}-{n}"
        d = os.path.join(ROOT, pid)
        n += 1
    os.makedirs(d)
    json.dump(script, open(os.path.join(d, "script.json"), "w"), indent=2, ensure_ascii=False)
    entry["project_id"] = pid
    entry["status"] = "scripted"
    entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    print(f"  -> project_id={pid}  ({len(script['scenes'])} scenes, title={script['title']!r})")
    return pid


def main():
    all_ = "--all" in sys.argv
    q = load_queue()
    pending = [e for e in q["queue"] if e.get("status") == "pending"]
    if not pending:
        return  # silent — no output => no delivery (watchdog pattern)
    env = load_env()
    todo = pending if all_ else pending[:1]
    print(f"processing {len(todo)} pending topic(s)")
    for entry in todo:
        try:
            process_one(entry, env)
        except Exception as ex:
            print(f"ERROR on '{entry['topic']}': {ex}", file=sys.stderr)
            entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    save_queue(q)
    print("queue updated")


if __name__ == "__main__":
    main()
