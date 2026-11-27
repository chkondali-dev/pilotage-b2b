# coding: utf-8
"""Migration du registre : seed de l'historique + nouvelles colonnes."""
import business.conventions as conv

rows = conv._read()
n = 0
for r in rows:
    if not str(r.get("historique", "") or "").strip():
        d = (r.get("date_debut_prospection") or "").strip()
        if d:
            r["historique"] = f"{d}:—>{r.get('statut', 'Prospection')}"
            n += 1
conv._write(rows)
print("seed historique:", n, "| rows:", len(rows))
print(open(conv.REGISTRY_PATH, encoding="utf-8").readline().strip())
