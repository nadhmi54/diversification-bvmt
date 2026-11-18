"""Construction du jeu de données BVMT 2023 -> date d'extraction (tronc commun, semaine 2).

Entrées (data/raw, data/interim) :
  - archives officielles BVMT histo_cotation_{2023,2024,2025}.zip et histo_indice_{...}.zip
  - data/interim/bulletins_2026.csv (src/parse_bulletins.py) et tunindex_2026.csv (src/parse_tunindex_bulletins.py)
Sorties (data/processed) : voir README.

Choix documentés (cf. note qualité) :
  * Cours de référence : dans les archives 2022-2025, la colonne OUVERTURE est le cours de référence de la
    séance (égal à la clôture de la veille dans 99,5 % des cas) ; dans les bulletins 2026, la colonne
    « Cours de référence » est lue directement.
  * Opérations sur titres (OST) : un jour où référence_t != clôture_{t-1}, la Bourse a ajusté le prix
    (dividende détaché, attribution gratuite, division du nominal). Facteur f_t = référence_t / clôture_{t-1}.
    Rendement du jour r_t = ln(clôture_t / référence_t) : le saut mécanique est neutralisé.
    Prix ajusté (rétroactif) : P*_t = P_t * prod_{s>t} f_s.
  * Séance parasite du 17/12/2025 (jour férié, clôtures à 0 et volumes nuls) supprimée.
"""
from __future__ import annotations
import io, re, zipfile, json
from pathlib import Path
import numpy as np
import pandas as pd

RAW = Path("data/raw/archives"); INTERIM = Path("data/interim"); OUT = Path("data/processed")
GROUPES_ACTIONS = {"11", "12", "13", "99", "51", "52", "53"}
DATE_DEBUT = pd.Timestamp("2023-01-01")
SEANCES_PARASITES = [pd.Timestamp("2025-12-17")]
SEUIL_LIQUIDITE = 0.60          # part minimale de séances avec au moins une transaction
HISTORIQUE_MIN_ANS = 2          # historique minimal de cotation avant la date d'extraction
TOL_OST = 0.0005                # |f-1| sous ce seuil = arrondi, pas une OST

def lire_archive_cotations(annee: int) -> pd.DataFrame:
    z = zipfile.ZipFile(RAW / f"bvmt_histo_cotation_{annee}.zip")
    frames = []
    for inf in z.infolist():
        if str(annee) not in Path(inf.filename).name:
            continue          # l'archive 2023 contient aussi le fichier 2022
        df = pd.read_csv(io.BytesIO(z.read(inf)), sep=";", encoding="latin-1", dtype=str)
        df.columns = [c.strip() for c in df.columns]
        frames.append(df.apply(lambda s: s.str.strip()))
    df = pd.concat(frames)
    df["source"] = f"bvmt.com.tn histo_cotation_{annee}.zip"
    return df

def lire_archive_indices(annee: int) -> pd.DataFrame:
    z = zipfile.ZipFile(RAW / f"bvmt_histo_indice_{annee}.zip")
    df = pd.read_csv(io.BytesIO(z.read(z.infolist()[0])), sep=";", encoding="latin-1", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df.apply(lambda s: s.str.strip())
    return df

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # ---------------- 1. archives 2023-2025 ----------------
    a = pd.concat([lire_archive_cotations(y) for y in (2023, 2024, 2025)])
    tout = a.copy()
    a = a[a.GROUPE.isin(GROUPES_ACTIONS)].copy()
    num = ["OUVERTURE", "CLOTURE", "PLUS_BAS", "PLUS_HAUT", "QUANTITE_NEGOCIEE", "NB_TRANSACTION", "CAPITAUX"]
    for c in num:
        a[c] = pd.to_numeric(a[c])
    a["date"] = pd.to_datetime(a.SEANCE, format="%d/%m/%Y")
    a = a[(a.date >= DATE_DEBUT) & ~a.date.isin(SEANCES_PARASITES)]
    arch = pd.DataFrame({
        "date": a.date, "isin": a.CODE, "nom": a.VALEUR, "groupe": a.GROUPE,
        "reference": a.OUVERTURE, "cloture": a.CLOTURE,
        "haut": a.PLUS_HAUT.where(a.QUANTITE_NEGOCIEE > 0), "bas": a.PLUS_BAS.where(a.QUANTITE_NEGOCIEE > 0),
        "volume": a.QUANTITE_NEGOCIEE, "nb_transactions": a.NB_TRANSACTION, "capitaux": a.CAPITAUX,
        "echange": a.QUANTITE_NEGOCIEE > 0, "source": a.source})
    # ---------------- 2. bulletins 2026 ----------------
    b = pd.read_csv(INTERIM / "bulletins_2026.csv", parse_dates=["seance"])
    bul = pd.DataFrame({
        "date": b.seance, "isin": b["isin"], "nom": b.valeur, "groupe": b.groupe.astype(str),
        "reference": b.reference, "cloture": b.cloture, "haut": b.haut, "bas": b.bas,
        "volume": np.nan, "nb_transactions": np.nan, "capitaux": np.nan,
        "echange": b.echange.astype(bool), "source": "Bulletin officiel BVMT " + b.fichier})
    mnemo = b.sort_values("seance").groupby("isin").mnemo.last()
    divs = b[["isin", "mnemo", "div_montant", "div_date"]].dropna().drop_duplicates()
    px = pd.concat([arch, bul]).sort_values(["isin", "date"]).reset_index(drop=True)
    px["ticker"] = px["isin"].map(mnemo)
    px["nom"] = px.groupby("isin").nom.transform("last")
    # ---------------- 3. OST : facteur d'ajustement ----------------
    px["cloture_veille"] = px.groupby("isin").cloture.shift()
    px["facteur"] = px.reference / px.cloture_veille
    ost = px[(px.facteur - 1).abs() > TOL_OST].copy()
    # libellés : dividendes connus (bulletins 2026 : dernier dividende de chaque titre), droits d'attribution
    divs["div_date"] = pd.to_datetime(divs.div_date, format="%d/%m/%Y", errors="coerce")
    div_set = {(r.isin, r.div_date): r.div_montant for r in divs.itertuples()}
    droits = tout[tout.GROUPE == "32"][["VALEUR", "CODE"]].drop_duplicates()
    da = []
    for r in droits.itertuples():
        m = re.search(r"^(.*?)\s*-?\s*DA\s*(\d+)\s*/\s*(\d+)\s*(\d{6})", r.VALEUR.upper())
        if m:
            d = pd.to_datetime(m[4], format="%d%m%y", errors="coerce")
            da.append({"prefixe": re.sub(r"[^A-Z]", "", m[1]), "k": int(m[2]), "n": int(m[3]),
                       "date": d, "droit": r.VALEUR})
    da = pd.DataFrame(da)
    def libelle(r):
        isin, date = r["isin"], r["date"]
        ecart = r.cloture_veille - r.reference
        if (isin, date) in div_set:
            return "dividende", f"dividende {div_set[(isin, date)]:.3f} DT (bulletin)"
        if len(da):
            proches = da[(da.date - date).abs() <= pd.Timedelta(days=3)]
            tic = re.sub(r"[^A-Z]", "", str(r["ticker"]).upper()); nom = re.sub(r"[^A-Z]", "", str(r["nom"]).upper())
            for x in proches.itertuples():
                f_th = x.n / (x.n + x.k)
                meme_societe = x.prefixe and (x.prefixe == tic or nom.startswith(x.prefixe))
                if abs(f_th - r["facteur"]) < 0.005 or (meme_societe and x.date == date):
                    extra = "" if abs(f_th - r["facteur"]) < 0.005 else " + autre ajustement (nominal/dividende)"
                    return "attribution gratuite", f"{x.droit} : {x.k} nouvelle(s) pour {x.n} anciennes (f théorique {f_th:.4f}){extra}"
        if r.facteur < 1 and r.facteur >= 0.75:
            return "dividende probable", f"écart {ecart:.3f} DT ({(1-r.facteur):.1%})"
        if r.facteur < 0.75:
            return "division / attribution probable", f"facteur {r.facteur:.4f}"
        return "ajustement à la hausse (reprise de cotation ?)", f"facteur {r.facteur:.4f}"
    if len(ost):
        lab = ost.apply(libelle, axis=1, result_type="expand")
        ost["type"], ost["detail"] = lab[0], lab[1]
    ost = ost[["date", "isin", "ticker", "nom", "cloture_veille", "reference", "facteur", "type", "detail", "source"]]
    # ---------------- 4. rendements et prix ajustés ----------------
    px["facteur"] = px.facteur.where((px.facteur - 1).abs() > TOL_OST, 1.0).fillna(1.0)
    px["rendement_log"] = np.log(px.cloture / px.reference)
    px.loc[px.groupby("isin").head(1).index, "rendement_log"] = np.nan
    # facteur cumulé rétroactif : produit des facteurs postérieurs à t
    px["fact_cum"] = px.groupby("isin").facteur.transform(lambda f: f[::-1].cumprod()[::-1].shift(-1).fillna(1.0))
    px["cloture_ajustee"] = px.cloture * px.fact_cum
    # ---------------- 5. Tunindex ----------------
    ind = pd.concat([lire_archive_indices(y) for y in (2023, 2024, 2025)])
    ind = ind[ind.LIB_INDICE.str.upper().isin(["TUNINDEX", "TUNINDEX20"])]
    ind["date"] = pd.to_datetime(ind.SEANCE, format="%d/%m/%Y")
    ind = ind.pivot_table(index="date", columns=ind.LIB_INDICE.str.lower(), values="INDICE_JOUR", aggfunc="first").astype(float)
    t26 = pd.read_csv(INTERIM / "tunindex_2026.csv", parse_dates=["seance"]).set_index("seance")[["tunindex", "tunindex20"]]
    tun = pd.concat([ind[["tunindex", "tunindex20"]], t26]).sort_index()
    tun = tun[(tun.index >= DATE_DEBUT) & ~tun.index.isin(SEANCES_PARASITES)]
    tun.index.name = "date"
    tun["rendement_log"] = np.log(tun.tunindex).diff()
    # ---------------- 6. univers et filtres ----------------
    date_extr = px.date.max()
    seances = pd.Index(sorted(px.date.unique()))
    cotes = px[px.date == date_extr]["isin"].unique()
    st = px.groupby("isin").agg(ticker=("ticker", "last"), nom=("nom", "last"), groupe=("groupe", "last"),
                                premiere_seance=("date", "min"), derniere_seance=("date", "max"),
                                nb_lignes=("date", "size"), part_seances_echangees=("echange", "mean"),
                                capitaux_median_2023_2025=("capitaux", "median"))
    st["cote_au_" + date_extr.strftime("%Y%m%d")] = st.index.isin(cotes)
    st["seances_manquantes"] = len(seances) - st.nb_lignes
    st["part_rendements_nuls"] = px.groupby("isin").rendement_log.apply(lambda r: (r.dropna() == 0).mean())
    def motif(r):
        if not r["cote_au_" + date_extr.strftime("%Y%m%d")]:
            return f"non coté au {date_extr:%d/%m/%Y} (dernière séance {r.derniere_seance:%d/%m/%Y})"
        if r.premiere_seance > date_extr - pd.DateOffset(years=HISTORIQUE_MIN_ANS):
            return f"historique < {HISTORIQUE_MIN_ANS} ans"
        if r.part_seances_echangees < SEUIL_LIQUIDITE:
            return f"liquidité insuffisante ({r.part_seances_echangees:.0%} des séances échangées < {SEUIL_LIQUIDITE:.0%})"
        return ""
    st["motif_exclusion"] = st.apply(motif, axis=1)
    st["retenu"] = st.motif_exclusion == ""
    retenus = st[st.retenu].index
    # ---------------- 7. exports ----------------
    cols = ["date", "isin", "ticker", "nom", "groupe", "reference", "cloture", "haut", "bas", "volume",
            "nb_transactions", "capitaux", "echange", "facteur", "cloture_ajustee", "rendement_log", "source"]
    px[cols].to_csv(OUT / "cotations_long.csv", index=False)
    u = px[px["isin"].isin(retenus)]
    lab = st.loc[retenus, "ticker"]
    u.pivot(index="date", columns="isin", values="cloture_ajustee").rename(columns=lab).to_csv(OUT / "prix_ajustes.csv")
    u.pivot(index="date", columns="isin", values="rendement_log").rename(columns=lab).iloc[1:].to_csv(OUT / "rendements_log.csv")
    u.pivot(index="date", columns="isin", values="echange").rename(columns=lab).astype(int).to_csv(OUT / "jours_echanges.csv")
    tun.to_csv(OUT / "tunindex.csv")
    ost.sort_values(["date", "isin"]).to_csv(OUT / "operations_sur_titres.csv", index=False)
    st.reset_index().to_csv(OUT / "univers.csv", index=False)
    meta = {"date_extraction_donnees": "2026-11-04", "derniere_seance": f"{date_extr:%Y-%m-%d}",
            "premiere_seance": f"{px.date.min():%Y-%m-%d}", "nb_seances": len(seances),
            "titres_dans_les_sources": int(st.shape[0]), "titres_cotes": int(len(cotes)),
            "titres_retenus": int(len(retenus)), "seuil_liquidite": SEUIL_LIQUIDITE,
            "historique_min_ans": HISTORIQUE_MIN_ANS, "nb_ost_detectees": int(len(ost))}
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    print(ost.type.value_counts())

if __name__ == "__main__":
    main()
