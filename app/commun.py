"""Fonctions communes à toutes les pages de l'interface.

Les calculs reprennent exactement ceux des notebooks S3, S4 et S4b (mêmes paramètres, même graine) :
avec les réglages par défaut, l'interface redonne les résultats du projet. Le script
app/verifier_coherence.py le contrôle.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import streamlit as st
from scipy import optimize
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score

RACINE = Path(__file__).resolve().parent.parent
P = RACINE / "data" / "processed"
S3 = RACINE / "data" / "s3"

GRAINE = 42
K_PLAGE = range(3, 9)
TAUX_IF = [0.03, 0.05, 0.08, 0.10]
SEUIL_LIQUIDITE = 0.60
NAVY, ORANGE, BLEU, ROUGE, GRIS = "#1F3A5F", "#E07A1F", "#4A7FB5", "#C0392B", "#8A94A6"
PALETTE = ["#1F3A5F", "#E07A1F", "#2E8B57", "#8E44AD", "#C0392B", "#4A7FB5", "#B7950B", "#6D4C41", "#17A589", "#7F8C8D"]

LIB = {"rendement_annualise": "Rendement", "volatilite_annualisee": "Volatilité", "skewness": "Skewness",
       "kurtosis": "Kurtosis", "var_95": "VaR 95 %", "cvar_95": "CVaR 95 %", "beta": "Bêta"}
F7 = list(LIB)
F5 = ["rendement_annualise", "volatilite_annualisee", "skewness", "cvar_95", "beta"]
ESPACES = {
    "7F": "7 features (S4)",
    "5F": "5 features sans redondance (S4b)",
    "ACP": "7 features après ACP (S4)",
    "RV": "Rendement-volatilité (plan de l'article)",
}


# ---------------------------------------------------------------- mise en page
def page(titre, sous_titre=None):
    st.set_page_config(page_title=f"{titre} · BVMT", page_icon="📈", layout="wide")
    st.markdown(f"""<style>
      .block-container {{padding-top: 2rem;}}
      h1, h2, h3 {{color: {NAVY};}}
      div[data-testid="stMetricValue"] {{color: {ORANGE}; font-weight: 700;}}
      .note {{background:#EEF2F7; border-radius:8px; padding:0.8rem 1rem; margin:0.4rem 0 1rem 0;}}
      .alerte {{background:#FDF0E6; border-radius:8px; padding:0.8rem 1rem; margin:0.4rem 0 1rem 0;}}
    </style>""", unsafe_allow_html=True)
    st.title(titre)
    if sous_titre:
        st.caption(sous_titre)
    with st.sidebar:
        st.markdown("**Diversification non supervisée · BVMT**")
        st.caption("Projet Math en assurance et finance · ESPRIT 5INFINI · données du 02/01/2023 au 03/11/2026")


def note(texte, alerte=False):
    st.markdown(f'<div class="{"alerte" if alerte else "note"}">{texte}</div>', unsafe_allow_html=True)


def pct(x, d=1):
    return f"{x * 100:.{d}f} %".replace(".", ",")


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


# ---------------------------------------------------------------- données
@st.cache_data
def qualite():
    q = pd.read_csv(P / "qualite_par_titre.csv").dropna(subset=["ticker"]).set_index("ticker")
    q["liquide"] = q["retenu"].astype(bool) if q["retenu"].dtype != object else q["retenu"].astype(str).eq("True")
    return q


@st.cache_data
def features():
    return pd.read_csv(S3 / "features_titres.csv").set_index("ticker")


@st.cache_data
def info():
    """Nom et liquidité des 75 titres de l'univers."""
    f = features(); q = qualite().loc[f.index]
    i = q[["nom", "groupe", "part_seances_echangees", "part_rendements_nuls", "capitaux_median_2023_2025", "nb_ost"]].copy()
    i["liquide"] = i["part_seances_echangees"] >= SEUIL_LIQUIDITE
    return i


@st.cache_data
def cotations():
    c = pd.read_csv(P / "cotations_long.csv", parse_dates=["date"],
                    usecols=["date", "ticker", "nom", "reference", "cloture", "capitaux", "echange", "facteur", "cloture_ajustee"])
    return c


@st.cache_data
def tunindex():
    return pd.read_csv(P / "tunindex.csv", parse_dates=["date"]).set_index("date")


@st.cache_data
def covariance():
    return pd.read_csv(S3 / "covariance_annualisee.csv", index_col=0)


@st.cache_data
def taux_sans_risque():
    return json.load(open(S3 / "taux_sans_risque.json", encoding="utf-8"))


def univers(liquides_seulement):
    i = info()
    return i.index[i.liquide] if liquides_seulement else i.index


# ---------------------------------------------------------------- Markowitz (S3)
def perf(w, mu, S, rf):
    r = float(w @ mu); v = float(np.sqrt(w @ S @ w))
    return r, v, (r - rf) / v


def _qp(S, mu=None, cible=None):
    n = len(S)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(n)}]
    if cible is not None:
        cons.append({"type": "eq", "fun": lambda w: w @ mu - cible, "jac": lambda w: mu})
    res = optimize.minimize(lambda w: w @ S @ w, np.full(n, 1 / n), jac=lambda w: 2 * S @ w, bounds=[(0, 1)] * n,
                            constraints=cons, method="SLSQP", options={"ftol": 1e-14, "maxiter": 1000})
    w = np.clip(res.x, 0, None); return w / w.sum()


def _max_sharpe(S, mu, rf):
    n = len(S); e = mu - rf
    i0 = np.argmax(e / np.sqrt(np.diag(S))); y0 = np.zeros(n); y0[i0] = 1 / e[i0]
    res = optimize.minimize(lambda y: y @ S @ y, y0, jac=lambda y: 2 * S @ y, bounds=[(0, None)] * n,
                            constraints=[{"type": "eq", "fun": lambda y: y @ e - 1, "jac": lambda y: e}],
                            method="SLSQP", options={"ftol": 1e-15, "maxiter": 2000})
    y = np.clip(res.x, 0, None); return y / y.sum()


@st.cache_data(show_spinner="Optimisation de Markowitz…")
def markowitz(liquides_seulement, rf, n_points=40):
    """Variance minimale, Sharpe maximal et frontière efficiente, sans vente à découvert (comme la S3)."""
    t = list(univers(liquides_seulement))
    mu = features().loc[t, "rendement_annualise"].values
    S = covariance().loc[t, t].values
    w_gmv = _qp(S); w_ms = _max_sharpe(S, mu, rf)
    r_min, r_max = float(w_gmv @ mu), float(mu.max())
    pts = []
    for m in np.linspace(r_min, r_max, n_points):
        w = _qp(S, mu, m) if m > r_min + 1e-9 else w_gmv
        pts.append(perf(w, mu, S, rf))
    pts.append(perf(w_ms, mu, S, rf))
    front = pd.DataFrame(pts, columns=["rendement", "volatilite", "sharpe"]).sort_values("rendement")
    w_n = np.full(len(t), 1 / len(t))
    rng = np.random.default_rng(0); W = rng.dirichlet(np.ones(len(t)) * 0.3, 20000)
    sr_alea = (W @ mu - rf) / np.sqrt(np.einsum("ij,jk,ik->i", W, S, W))
    return {"tickers": t, "front": front,
            "gmv": pd.Series(w_gmv, index=t), "ms": pd.Series(w_ms, index=t),
            "perf_gmv": perf(w_gmv, mu, S, rf), "perf_ms": perf(w_ms, mu, S, rf), "perf_1n": perf(w_n, mu, S, rf),
            "sharpe_alea_max": float(sr_alea.max())}


# ---------------------------------------------------------------- segmentation (S4 / S4b)
def standardiser(F):
    return pd.DataFrame(StandardScaler().fit_transform(F), index=F.index, columns=F.columns)


@st.cache_data
def espace(nom, liquides_seulement):
    """Coordonnées standardisées des titres dans un espace, comme dans les notebooks."""
    t = univers(liquides_seulement); F = features().loc[t]
    if nom == "RV":
        return standardiser(F[["rendement_annualise", "volatilite_annualisee"]])
    if nom == "5F":
        return standardiser(F[F5])
    Z = standardiser(F[F7])
    if nom == "7F":
        return Z
    p = PCA(random_state=GRAINE).fit(Z)
    n80 = int(np.argmax(p.explained_variance_ratio_.cumsum() >= 0.80) + 1)
    q = PCA(n_components=n80, random_state=GRAINE).fit(Z)
    return pd.DataFrame(q.transform(Z), index=Z.index, columns=[f"PC{i+1}" for i in range(n80)])


def _coude(ks, inerties):
    x = (np.array(ks) - ks[0]) / (ks[-1] - ks[0])
    y = (np.array(inerties) - min(inerties)) / (max(inerties) - min(inerties))
    return ks[int(np.argmax((1 - x) - y))]


def _kmeans(X, k):
    return KMeans(n_clusters=k, init="k-means++", n_init=50, random_state=GRAINE).fit(X)


@st.cache_data(show_spinner="Calcul des critères pour k…")
def criteres_k(nom, liquides_seulement):
    X = espace(nom, liquides_seulement); lignes = []
    for k in range(2, 11):
        km = _kmeans(X, k); tailles = np.bincount(km.labels_)
        lignes.append({"k": k, "inertie": km.inertia_, "silhouette": silhouette_score(X, km.labels_),
                       "calinski_harabasz": calinski_harabasz_score(X, km.labels_),
                       "davies_bouldin": davies_bouldin_score(X, km.labels_),
                       "tailles": " / ".join(map(str, sorted(tailles, reverse=True))), "dans_la_plage": k in K_PLAGE})
    t = pd.DataFrame(lignes).set_index("k")
    p = t[t.dans_la_plage]; ks = list(p.index)
    votes = {"Coude": _coude(ks, p.inertie.tolist()), "Silhouette": int(p.silhouette.idxmax()),
             "Calinski-Harabasz": int(p.calinski_harabasz.idxmax()), "Davies-Bouldin": int(p.davies_bouldin.idxmin())}
    compte = pd.Series(list(votes.values())).value_counts()
    meilleurs = compte[compte == compte.max()].index.tolist()
    k_ret = int(max(meilleurs, key=lambda k: p.silhouette[k]))
    return t, votes, k_ret


@st.cache_data
def clusters(nom, liquides_seulement, k):
    """Étiquettes k-means, numérotées du plus grand cluster (1) au plus petit, comme dans les notebooks."""
    X = espace(nom, liquides_seulement); km = _kmeans(X, k)
    ordre = pd.Series(km.labels_).value_counts().index
    return pd.Series(pd.Series(km.labels_).map({c: i + 1 for i, c in enumerate(ordre)}).values, index=X.index, name="cluster")


@st.cache_data
def scores_if(nom, liquides_seulement):
    """Score d'anomalie Isolation Forest (500 arbres, graine 42) : plus haut = plus anormal."""
    X = espace(nom, liquides_seulement)
    f = IsolationForest(n_estimators=500, contamination="auto", random_state=GRAINE).fit(X)
    return pd.Series(-f.score_samples(X), index=X.index, name="score")


def signales(scores, taux):
    n = int(np.ceil(taux * len(scores)))
    return scores.index.isin(scores.nlargest(n).index)


def nature(ticker, Z):
    """Règle de la S4 : artefact d'illiquidité, performance extrême ou atypique modéré."""
    i = info().loc[ticker]; z = Z.loc[ticker]
    ext = [f"{LIB.get(f, f)} {'+' if z[f] > 0 else '−'}{abs(z[f]):.1f}σ" for f in Z.columns if abs(z[f]) > 2]
    if i.part_seances_echangees < SEUIL_LIQUIDITE or i.part_rendements_nuls > 0.5:
        return "Artefact d'illiquidité", (f"échangé {pct(i.part_seances_echangees, 0)} des séances, "
                                          f"{pct(i.part_rendements_nuls, 0)} de rendements nuls" + (f" ; extrêmes : {', '.join(ext)}" if ext else ""))
    if ext:
        sens = ""
        if "rendement_annualise" in z.index and abs(z.rendement_annualise) > 2:
            sens = " (hausse)" if z.rendement_annualise > 0 else " (baisse)"
        return "Performance extrême" + sens, f"liquide ({pct(i.part_seances_echangees, 0)}) ; extrêmes : {', '.join(ext)}"
    return "Atypique modéré", f"liquide ({pct(i.part_seances_echangees, 0)}) ; aucune feature à |z| > 2, isolé par une combinaison de features"


def z_features(liquides_seulement, cols=None):
    t = univers(liquides_seulement)
    return standardiser(features().loc[t, cols or F7])


@st.cache_data
def plan_affichage(nom, liquides_seulement):
    """Plan 2D pour dessiner les titres : l'espace lui-même pour RV, sinon PC1-PC2 de l'espace."""
    X = espace(nom, liquides_seulement)
    if X.shape[1] == 2:
        return X.set_axis(["axe 1", "axe 2"], axis=1), ("Rendement standardisé", "Volatilité standardisée")
    p = PCA(n_components=2, random_state=GRAINE).fit(X)
    return pd.DataFrame(p.transform(X), index=X.index, columns=["axe 1", "axe 2"]), (
        f"PC1 ({pct(p.explained_variance_ratio_[0], 0)})", f"PC2 ({pct(p.explained_variance_ratio_[1], 0)})")


@st.cache_data
def stabilite_anomalies(liquides_seulement, espaces=("RV", "7F", "ACP")):
    """Nombre de signalements par titre sur espaces × 4 taux (12 tests en S4)."""
    nb = None
    for e in espaces:
        s = scores_if(e, liquides_seulement)
        for t in TAUX_IF:
            v = pd.Series(signales(s, t).astype(int), index=s.index)
            nb = v if nb is None else nb + v
    return nb
