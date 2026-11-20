import re, csv, glob, os, sys
root = sys.argv[1]
rows = []
for f in sorted(glob.glob(os.path.join(root, "agents", "*.md"))):
    agent = os.path.basename(f).split("_")[0]
    txt = open(f, encoding="utf-8").read()
    for blk in re.split(r"\n### ", txt)[1:]:
        lines = blk.splitlines()
        pid = lines[0].strip()
        body = "\n".join(lines[1:])
        if "Scores" not in body and "Class" not in body:
            continue
        def g(pat):
            m = re.search(pat, body)
            return m.group(1).strip() if m else ""
        title = g(r"Title[^:\n]*:\s*(.+)")
        ver = g(r"verified:\s*([^;\n]+)")
        peer = g(r"peer_reviewed:\s*([^\n]+)")
        cls = g(r"Class:\s*(.+)")
        sc = g(r"Scores:\s*(.+)")
        ev = g(r"Evidence strength:\s*(.+)")
        rows.append(dict(agent=agent, id=pid, title=title[:200], verified=ver[:80], peer=peer[:60], cls=cls[:120], scores=sc[:160], evidence=ev[:40]))
out = os.path.join(root, "final", "master_db_raw.csv")
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), "rows ->", out)
