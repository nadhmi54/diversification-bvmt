"""Extraction des cours des actions depuis les Bulletins Officiels quotidiens de la BVMT (PDF).

Deux mises en page sont gérées (ancien site bvmt.com.tn jusqu'au 13/04/2026, nouveau site
tunis-stockexchange.com ensuite). Les colonnes sont repérées par leur en-tête, pas par leur position.
On garde les titres de capital (groupes 11, 12, 13, 99, 5x) et on ignore droits (32), obligations (21), etc.

Sortie : une ligne par (séance, ISIN) avec cours de référence, ouverture, plus haut, plus bas,
clôture, dernier dividende (montant, date) et un indicateur 'echange' (vrai si au moins une transaction :
ouverture/haut/bas renseignés). Les bulletins ne donnent pas les volumes du marché principal.
"""
from __future__ import annotations
import re, sys, datetime as dt
from pathlib import Path
import pandas as pd
import pymupdf

RE_ISIN = re.compile(r"^TN[A-Z0-9]{10}$")
RE_GROUPE = re.compile(r"Groupe\s*(\d+)", re.I)
MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre",
        "octobre", "novembre", "decembre"]
GROUPES_ACTIONS = {"11", "12", "13", "99", "51", "52", "53"}

# motif d'en-tête -> nom de colonne (texte d'en-tête normalisé : minuscules, sans accents ni retours)
ENTETES = [("code isin", "isin"), ("mnemo", "mnemo"), ("nomina", "nominal"),
           ("cours de", "reference"), ("ouverture", "ouverture"), ("dernier cours", "dernier"),
           ("plus haut", "haut"), ("plus bas", "bas"), ("cloture", "cloture"), ("valeurs", "valeur")]


def norm(s) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\n", " ").lower()
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("ô", "o"), ("û", "u"), ("à", "a"), ("î", "i")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def nombre(s) -> float | None:
    s = "" if s is None else str(s).strip().replace(" ", "").replace(" ", "")
    if not s or not re.fullmatch(r"-?\d+(,\d+)?", s):
        return None
    return float(s.replace(",", "."))


def date_du_texte(doc) -> dt.date | None:
    t = norm(doc[0].get_text() + " " + (doc[1].get_text() if doc.page_count > 1 else ""))
    m = re.search(r"(lundi|mardi|mercredi|jeudi|vendredi) (\d{1,2}) (\w+) (\d{4})", t)
    if m and m[3] in MOIS:
        return dt.date(int(m[4]), MOIS.index(m[3]) + 1, int(m[2]))
    return None


def mapping_entete(row) -> dict[str, int] | None:
    cells = [norm(c) for c in row]
    if not any("code isin" in c for c in cells) or not any("cloture" in c for c in cells):
        return None
    m = {}
    for i, c in enumerate(cells):
        for motif, nom in ENTETES:
            if nom not in m and c.startswith(motif) or (nom not in m and motif in c and nom in ("reference", "cloture", "ouverture")):
                if nom not in m:
                    m[nom] = i
                    break
    # 'Dernier Dividende' commence aussi par 'dernier' : on le repère pour le montant/date
    for i, c in enumerate(cells):
        if c.startswith("dernier dividende"):
            m["div_montant"] = i
            m["div_date"] = i + 1
    return m if {"isin", "reference", "cloture"} <= m.keys() else None


def lire_bulletin(path: Path) -> tuple[dt.date, list[dict]]:
    doc = pymupdf.open(path)
    d_texte = date_du_texte(doc)
    m = re.search(r"(\d{8})", path.name)
    d_nom = dt.datetime.strptime(m[1], "%Y%m%d").date() if m else None
    if d_nom and d_texte and d_nom != d_texte:
        raise ValueError(f"{path.name}: date du nom {d_nom} != date imprimée {d_texte}")
    seance = d_texte or d_nom
    lignes, mapping = [], None
    for page in doc:
        if "MARCHE OBLIGATAIRE" in page.get_text().upper() and page.number > 0:
            break  # les actions sont avant la cote obligataire
        for tab in page.find_tables().tables:
            for row in tab.extract():
                mp = mapping_entete(row)
                if mp:
                    mapping = mp
                    continue
                if mapping is None:
                    continue
                cells = [None if c is None else str(c).strip() for c in row]
                isin = next((c for c in cells if c and RE_ISIN.match(c)), None)
                if not isin:
                    continue
                g = next((RE_GROUPE.search(c) for c in cells if c and RE_GROUPE.search(c)), None)
                groupe = g[1] if g else None
                if groupe not in GROUPES_ACTIONS:
                    continue
                # décalage éventuel (colonne N° en tête dans le nouveau format)
                j = cells.index(isin) - mapping["isin"]
                get = lambda k: cells[mapping[k] + j] if k in mapping and 0 <= mapping[k] + j < len(cells) else None
                r = {"seance": seance, "isin": isin, "mnemo": get("mnemo"), "valeur": get("valeur"),
                     "groupe": groupe, "nominal": nombre(get("nominal")),
                     "reference": nombre(get("reference")), "ouverture": nombre(get("ouverture")),
                     "haut": nombre(get("haut")), "bas": nombre(get("bas")),
                     "cloture": nombre(get("cloture")),
                     "div_montant": nombre(get("div_montant")), "div_date": get("div_date"),
                     "fichier": path.name}
                r["echange"] = r["haut"] is not None and r["bas"] is not None
                lignes.append(r)
    return seance, lignes


def lire_dossier(dossier: Path) -> pd.DataFrame:
    rows, vus = [], {}
    for p in sorted(dossier.glob("*.pdf")):
        seance, lignes = lire_bulletin(p)
        if seance in vus:
            print(f"  doublon de séance {seance}: {p.name} et {vus[seance]} (on garde le second)")
            rows = [r for r in rows if r["seance"] != seance]
        vus[seance] = p.name
        rows += lignes
    df = pd.DataFrame(rows).drop_duplicates(["seance", "isin"])
    return df.sort_values(["seance", "isin"]).reset_index(drop=True)


if __name__ == "__main__":
    dossier = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/bulletins/pdf")
    df = lire_dossier(dossier)
    out = Path("data/interim/bulletins_2026.csv"); out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(df.shape, df.seance.min(), df.seance.max(), "titres:", df["isin"].nunique())
