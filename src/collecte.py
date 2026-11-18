"""Collecte reproductible des données brutes BVMT (2023 -> aujourd'hui).

1. Archives annuelles officielles (cotations + indices) :
   https://www.bvmt.com.tn/sites/default/files/historiques/cotations/histo_cotation_{annee}.zip
   https://www.bvmt.com.tn/sites/default/files/historiques/indices/histo_indice_{annee}.zip
2. Année en cours (pas encore archivée) : Bulletins officiels quotidiens de la cote (PDF)
   - jusqu'au 13/04/2026 : https://www.bvmt.com.tn/sites/default/files/bulletin/pdf/bullAAAAMMJJ.pdf
   - depuis le 14/04/2026 : liste lue sur https://tunis-stockexchange.com/editions-statistique?page=N
     (noms irréguliers : « Bull20261013-3.pdf », « Bull20261012 (2).pdf », « 2026-06/BO.pdf »)

Règles : fichiers publics uniquement, robots.txt respecté (aucune restriction à la date de collecte),
une requête toutes les DELAI secondes, pas de contournement d'authentification.
NB : la collecte du 04/11/2026 a été faite avec la même logique depuis un navigateur (le réseau de
l'environnement de travail filtrait ces sites) ; les fichiers obtenus sont dans data/raw/ et leurs URL
dans data/raw/bulletins/manifeste_bulletins.csv.

Usage : python src/collecte.py            (télécharge ce qui manque dans data/raw/)
"""
from __future__ import annotations
import datetime as dt, re, time, urllib.parse
from pathlib import Path
import requests

DELAI = 2.0
UA = {"User-Agent": "Mozilla/5.0 (projet etudiant ESPRIT 5INFINI - collecte donnees BVMT)"}
RAW = Path("data/raw")
BVMT = "https://www.bvmt.com.tn/sites/default/files"
TSE = "https://tunis-stockexchange.com"
BASCULE = dt.date(2026, 4, 14)      # changement de site de la Bourse

def get(s: requests.Session, url: str) -> requests.Response | None:
    time.sleep(DELAI)
    try:
        r = s.get(url, headers=UA, timeout=120)
        return r if r.status_code == 200 and len(r.content) > 0 else None
    except requests.RequestException as e:
        print("  erreur", url, e); return None

def archives(s, annees):
    out = RAW / "archives"; out.mkdir(parents=True, exist_ok=True)
    for a in annees:
        for kind, path in (("cotation", "cotations"), ("indice", "indices")):
            f = out / f"bvmt_histo_{kind}_{a}.zip"
            if f.exists(): continue
            r = get(s, f"{BVMT}/historiques/{path}/histo_{kind}_{a}.zip")
            if r is not None and r.content[:2] == b"PK":
                f.write_bytes(r.content); print("  OK", f.name)
            else:
                print("  absent", kind, a)

def liste_bulletins_tse(s, depuis: dt.date) -> dict[dt.date, str]:
    trouves: dict[dt.date, tuple[int, str]] = {}
    for page in range(60):
        r = get(s, f"{TSE}/editions-statistique?page={page}")
        if r is None: break
        dates = []
        for lien in set(re.findall(r"/sites/default/files/[^\"']+\.pdf", r.text)):
            nom = urllib.parse.unquote(lien)
            m = re.search(r"/Bull(\d{8})(?:[-_ ]?\(?(\d+)\)?)?\.pdf$", nom, re.I)
            if m:
                d = dt.datetime.strptime(m[1], "%Y%m%d").date(); dates.append(d)
                n = int(m[2]) if m[2] else -1
                if d not in trouves or n > trouves[d][0]:
                    trouves[d] = (n, TSE + lien)
            elif re.search(r"/\d{4}-\d\d/BO\.pdf$", nom):
                trouves.setdefault(dt.date(1900, 1, 1), (-9, TSE + lien))  # daté à la lecture (parse_bulletins)
        if dates and min(dates) < depuis: break
    return {d: u for d, (_, u) in trouves.items()}

def bulletins(s, debut: dt.date, fin: dt.date):
    out = RAW / "bulletins" / "pdf"; out.mkdir(parents=True, exist_ok=True)
    d = debut
    while d <= min(fin, BASCULE - dt.timedelta(days=1)):
        f = out / f"bull{d:%Y%m%d}.pdf"
        if d.weekday() < 5 and not f.exists():
            r = get(s, f"{BVMT}/bulletin/pdf/bull{d:%Y%m%d}.pdf")
            if r is not None and r.content[:4] == b"%PDF": f.write_bytes(r.content)
        d += dt.timedelta(days=1)
    if fin >= BASCULE:
        for jour, url in sorted(liste_bulletins_tse(s, BASCULE).items()):
            f = out / (f"Bull{jour:%Y%m%d}.pdf" if jour.year > 1900 else "BO_" + url.split("/")[-2] + ".pdf")
            if (jour >= BASCULE or jour.year == 1900) and jour <= fin and not f.exists():
                r = get(s, url)
                if r is not None and r.content[:4] == b"%PDF": f.write_bytes(r.content); print("  OK", f.name)

if __name__ == "__main__":
    aujourd_hui = dt.date.today()
    with requests.Session() as s:
        archives(s, range(2023, aujourd_hui.year))
        bulletins(s, dt.date(aujourd_hui.year, 1, 1), aujourd_hui - dt.timedelta(days=1))
