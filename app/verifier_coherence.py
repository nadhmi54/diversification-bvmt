"""Vérifie que l'interface redonne exactement les résultats des notebooks S3, S4 et S4b.

Lancer depuis la racine du projet :  python app/verifier_coherence.py
"""
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logging.getLogger("streamlit").setLevel(logging.ERROR)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as c  # noqa: E402

R4 = pd.read_csv(c.P / "s4" / "resultats_par_titre.csv").set_index("ticker")
R5 = pd.read_csv(c.P / "s4_5f" / "resultats_par_titre.csv").set_index("ticker")
ok = []


def test(nom, cond):
    ok.append(bool(cond)); print(("OK    " if cond else "ÉCHEC ") + nom)


# S4 et S4b : k retenus, clusters et Isolation Forest
attendus = {("RV", False): 8, ("7F", False): 3, ("ACP", False): 3, ("5F", False): 3, ("5F", True): 3}
for (e, liq), k in attendus.items():
    test(f"k retenu {e}{' liquides' if liq else ''} = {k}", c.criteres_k(e, liq)[2] == k)

for e in ["RV", "7F", "ACP"]:
    test(f"clusters {e} (75 titres) identiques à la S4", (c.clusters(e, False, c.criteres_k(e, False)[2]) == R4[f"cluster_{e}"]).all())
    test(f"scores IF {e} identiques à la S4", np.allclose(c.scores_if(e, False), R4[f"score_if_{e}"]))
    k57 = c.criteres_k(e, True)[2]; cl57 = c.clusters(e, True, k57)
    test(f"clusters {e} (57 liquides) identiques à la S4", (cl57 == R4.loc[cl57.index, f"cluster_{e}_liquides"]).all())
test("clusters 5F identiques à la S4b", (c.clusters("5F", False, 3) == R5["cluster_5F"]).all())
test("scores IF 5F identiques à la S4b", np.allclose(c.scores_if("5F", False), R5["score_if_5F"]))
test("nombre de signalements sur 12 identique à la S4", (c.stabilite_anomalies(False) == R4["nb_signalements_sur_12"]).all())

# S3 : Markowitz
rf = c.taux_sans_risque()["taux_continu_annuel_utilise"]
m = c.markowitz(False, rf)
ms = pd.read_csv(c.S3 / "markowitz_sharpe_maximal.csv").set_index("ticker")["poids"]
gmv = pd.read_csv(c.S3 / "markowitz_variance_minimale.csv").set_index("ticker")["poids_sans_vente_a_decouvert"]
test(f"Sharpe maximal = 4,93 (calculé {m['perf_ms'][2]:.3f})", round(m["perf_ms"][2], 2) == 4.93)
test("poids du Sharpe maximal identiques à la S3", np.allclose(m["ms"], ms.loc[m["ms"].index], atol=1e-4))
test("poids de la variance minimale identiques à la S3", np.allclose(m["gmv"], gmv.loc[m["gmv"].index], atol=1e-4))
test(f"meilleur portefeuille aléatoire = 3,22 (calculé {m['sharpe_alea_max']:.3f})", round(m["sharpe_alea_max"], 2) == 3.22)

print(f"\n{sum(ok)}/{len(ok)} contrôles réussis")
sys.exit(0 if all(ok) else 1)
