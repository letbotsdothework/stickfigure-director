import os, sys, shutil

ROOT = os.environ.get("PROJECTS_ROOT", "/opt/data/workspace/stickfigure-director")
pid = sys.argv[1]
d = os.path.join(ROOT, pid)
if not os.path.isdir(d):
    print("no such project:", pid)
    sys.exit(1)

# remove intermediate/regenerable directories
for sub in ("clips", "work", "clips_v3_prelim", "voice_test", "vo_cont"):
    p = os.path.join(d, sub)
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)
        print("removed dir:", sub)

# remove old/duplicate mp4 versions (keep current master + preview)
for f in os.listdir(d):
    if f.endswith(".mp4") and ("_v1" in f or "noflare" in f or "_old" in f):
        os.remove(os.path.join(d, f))
        print("removed file:", f)

print("cleanup complete for", pid)
