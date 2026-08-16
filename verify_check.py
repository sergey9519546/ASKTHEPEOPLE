import os, subprocess
for p in ['.kilo/anchored_memory.md','backend/app/models/task.py','docs/architecture/index.md']:
    print(p, "EXISTS" if os.path.isfile(p) else "MISSING")
print("HEAD:", subprocess.check_output(["git","rev-parse","--short","HEAD"]).decode().strip())
print("TRACKED_CLEAN:", "YES" if subprocess.call(["git","diff","--quiet","HEAD"])==0 else "NO")
print("UNTRACKED:", subprocess.check_output(["git","ls-files","--others","--exclude-standard","--directory"]).decode().strip() or "NONE")
with open(".kilo/anchored_memory.md") as f:
    lines = f.read().splitlines()
print("ANCHOR_LINES:", len(lines))
print("LAST_LINE:", lines[-1] if lines else "(empty)")
