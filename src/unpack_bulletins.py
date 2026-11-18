"""Décompresse un paquet de bulletins (format BVMTPACK1 produit par la collecte navigateur)
en fichiers PDF individuels + un manifeste CSV (nom, URL source, taille).

Format : ligne 'BVMTPACK1', ligne JSON {source, extracted_at, files:[{name,url,offset,size}]}, puis
les octets des PDF concaténés (offset relatif au début de la zone binaire).
Usage : python src/unpack_bulletins.py data/raw/bulletins/bvmt_bulletins_2026_bvmt.bin
"""
import csv, json, sys
from pathlib import Path

def unpack(pack: Path, out_dir: Path) -> list[dict]:
    raw = pack.read_bytes()
    l1 = raw.index(b"\n"); assert raw[:l1] == b"BVMTPACK1", "format inconnu"
    l2 = raw.index(b"\n", l1 + 1)
    meta = json.loads(raw[l1 + 1:l2].decode("utf-8"))
    body = raw[l2 + 1:]
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in meta["files"]:
        b = body[f["offset"]:f["offset"] + f["size"]]
        assert b[:4] == b"%PDF", f["name"]
        (out_dir / f["name"]).write_bytes(b)
        rows.append({"fichier": f["name"], "url": f["url"], "octets": f["size"],
                     "source": meta["source"], "extrait_le": meta["extracted_at"]})
    return rows

if __name__ == "__main__":
    allrows = []
    for p in sys.argv[1:]:
        p = Path(p)
        allrows += unpack(p, p.parent / "pdf")
    man = Path(sys.argv[1]).parent / "manifeste_bulletins.csv"
    old = list(csv.DictReader(man.open(encoding="utf-8"))) if man.exists() else []
    seen = {r["fichier"] for r in allrows}
    allrows = [r for r in old if r["fichier"] not in seen] + allrows
    with man.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["fichier", "url", "octets", "source", "extrait_le"])
        w.writeheader(); w.writerows(sorted(allrows, key=lambda r: r["fichier"][-12:]))
    print(len(allrows), "bulletins ->", man)
