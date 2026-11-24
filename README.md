# Diversification par apprentissage non supervisé sur la BVMT

Projet Math en assurance et finance — 5INFINI, ESPRIT, A.U. 2026-2027.

Le projet reprend, critique et prolonge l'article de Rebai, Boukhris, Ncib et Ben Lasmar (2021),
*Unsupervised Learning Diversification Applied on the Tunisian Stock Market Before and During the Covid-19 Crisis*.
Données : actions cotées à la Bourse de Tunis du **02/01/2023 au 03/11/2026** (extraction du 04/11/2026),
uniquement à partir de **sources officielles** de la Bourse (archives annuelles 2023-2025, bulletins officiels quotidiens 2026).

## Avancement

| Séance | Contenu | Où |
|---|---|---|
| S1 | Analyse critique de l'article de référence | rapport (hors dépôt) |
| S2 | Collecte, nettoyage, opérations sur titres, filtres, note qualité | `src/`, `data/processed/`, `reports/note_qualite_donnees.md` |
| S3 | 7 features par titre, covariance, Markowitz (variance minimale, Sharpe maximal, frontière) | `notebooks/S3_features_markowitz.ipynb`, `data/s3/`, `reports/S3_Features_Markowitz_BVMT.pdf` |
| S4 | Standardisation, ACP, k-means (3 espaces), Isolation Forest, interprétation, comparaison 75 / 57 titres | `notebooks/S4_segmentation_anomalies.ipynb`, `data/processed/s4/` |
| S4b | Même démarche avec 5 features (kurtosis et VaR retirés : corrélations 0,92 et 0,89 avec skewness et CVaR) ; comparaison avec la S4 | `notebooks/S4b_segmentation_5_features.ipynb`, `data/processed/s4_5f/` |
| S3 + S4 | Les trois notebooks réunis en un seul, dans l'ordre d'exécution (résultats identiques) | `notebooks/S3_S4_complet.ipynb` |
| Interface | Application Streamlit : données, paramètres, Markowitz, segmentation, anomalies, fiche par titre ; réglages pour explorer | `app/` |

## Structure

```
src/                     scripts de la S2 (collecte, extraction des bulletins PDF, construction du jeu de données)
notebooks/               S3, S4, S4b et le notebook réuni S3_S4_complet, exécutables de bout en bout (chemins relatifs, graine fixe)
data/raw/                données brutes — NON versionnées (voir ci-dessous), sauf manifeste_bulletins.csv
data/interim/            extractions intermédiaires des bulletins 2026
data/processed/          jeu de données de la S2 ; sorties de la S4 dans data/processed/s4/, de la S4b dans data/processed/s4_5f/
data/s3/                 sorties de la S3
app/                     interface Streamlit (Accueil.py, pages/, commun.py, verifier_coherence.py)
reports/                 note qualité (S2), rapport PDF de la S3, présentation, texte de présentation, explications frontière et choix de k
```

## Reproduire

```bash
pip install -r requirements.txt

# S2 — données (les données brutes ne sont pas dans le dépôt : on les retélécharge)
python src/collecte.py                                    # -> data/raw/  (sources officielles BVMT)
python src/parse_bulletins.py data/raw/bulletins/pdf      # -> data/interim/bulletins_2026.csv  (~3 min)
python src/parse_tunindex_bulletins.py                    # -> data/interim/tunindex_2026.csv
python src/build_dataset.py                               # -> data/processed/*

# S3 et S4 — à lancer depuis le dossier notebooks/
jupyter nbconvert --to notebook --execute --inplace notebooks/S3_features_markowitz.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/S4_segmentation_anomalies.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/S4b_segmentation_5_features.ipynb

# ou tout d'un coup (S3 + S4 + S4b)
jupyter nbconvert --to notebook --execute --inplace notebooks/S3_S4_complet.ipynb
```

### Interface (Streamlit)

L'interface présente tout le projet dans le navigateur : données, paramètres, Markowitz, segmentation, anomalies
et une fiche par titre. Elle lit les sorties des notebooks (`data/processed/`, `data/s3/`) et refait les calculs
avec les mêmes paramètres (graine 42) : par défaut, elle affiche exactement les résultats du projet.

#### 1. Installer les dépendances (une seule fois)

Depuis le dossier du projet :

```powershell
cd "chemin\vers\Projet Math Assurance"
python -m pip install -r requirements.txt
```

L'interface n'a besoin que de `pandas`, `numpy`, `scipy`, `scikit-learn`, `streamlit` et `plotly`. Si seule
l'installation de `jupyterlab` échoue sous Windows (erreur de chemin trop long), on peut l'ignorer : elle ne sert
pas à l'interface.

#### 2. Lancer l'interface

Toujours depuis le dossier du projet (pas depuis `app/`) :

```powershell
python -m streamlit run app/Accueil.py
```

Le navigateur s'ouvre sur <http://localhost:8501> (sinon, copier cette adresse dans Chrome ou Edge).
Au premier lancement, Streamlit peut demander une adresse e-mail : appuyer sur Entrée pour passer.

On utilise `python -m streamlit` plutôt que `streamlit` : avec le Python du Microsoft Store, la commande
`streamlit` seule n'est pas reconnue (elle n'est pas dans le PATH).

#### 3. Utiliser l'interface

| Page | Contenu | Réglages (barre de gauche) |
|---|---|---|
| Accueil | Chiffres clés, étapes, conclusions | — |
| Données | Liquidité des 75 titres ; cours brut et ajusté d'un titre avec ses opérations sur titres | choix du titre |
| Paramètres | Tableau des 7 features, corrélations, passage à 5 features | Pearson / Spearman, feature affichée |
| Markowitz | Frontière efficiente interactive, poids du Sharpe maximal et de la variance minimale | taux sans risque, titres liquides seulement |
| Segmentation | Vote des 4 critères pour k, carte des groupes, profil de chaque groupe | espace (7F, 5F, ACP, RV), k, titres liquides seulement |
| Anomalies | Scores Isolation Forest, nature de chaque anomalie, stabilité sur 12 tests | espace, taux de contamination, titres liquides seulement |
| Fiche titre | Features en écarts-types, groupe dans chaque espace, anomalie ou non, cours | choix du titre |

- Avec les réglages par défaut, chaque page affiche les résultats du projet (bandeau vert).
- Quand un réglage s'écarte des choix du projet, la page l'indique (bandeau orange) : c'est de l'exploration.
- La première ouverture des pages Markowitz et Segmentation prend quelques secondes, ensuite c'est instantané.

#### 4. Arrêter l'interface

Dans le terminal, appuyer sur **Ctrl+C**.

#### 5. Vérifier la cohérence avec les notebooks (facultatif)

```powershell
python app/verifier_coherence.py
```

Résultat attendu : `21/21 contrôles réussis` (k retenus, groupes, scores Isolation Forest et signalements identiques
à la S4 et à la S4b ; Sharpe 4,93, poids et meilleur portefeuille aléatoire identiques à la S3).

#### En cas de problème

| Message | Solution |
|---|---|
| `streamlit n'est pas reconnu` | utiliser `python -m streamlit run app/Accueil.py` |
| `No module named streamlit` (ou `plotly`, `sklearn`) | `python -m pip install streamlit plotly scikit-learn` |
| `File does not exist: app/Accueil.py` | se placer dans le dossier du projet, pas dans `app/` |
| `FileNotFoundError` sur un fichier de `data/` | exécuter d'abord les notebooks (S3, S4, S4b) pour produire leurs sorties |
| Le port 8501 est déjà utilisé | `python -m streamlit run app/Accueil.py --server.port 8502` |

#### Organisation du code

```
app/
  Accueil.py               page d'accueil (point d'entrée)
  commun.py                chargement des données et calculs partagés (Markowitz, k-means, Isolation Forest)
  verifier_coherence.py    contrôle : l'interface redonne les résultats des notebooks
  pages/                   une page par étape (Données, Paramètres, Markowitz, Segmentation, Anomalies, Fiche titre)
.streamlit/config.toml     couleurs de l'interface
```

`src/unpack_bulletins.py` ne sert que pour les paquets `.bin` produits par la collecte initiale faite depuis un navigateur.
La liste exacte des 209 bulletins utilisés (URL, taille, date d'extraction) est dans `data/raw/bulletins/manifeste_bulletins.csv`.

## Choix principaux

- **Univers** : 75 actions cotées au 03/11/2026, dont 57 liquides (au moins 60 % de séances avec une transaction).
  Les résultats sont donnés sur les 75 titres et sur les 57 titres liquides.
- **Opérations sur titres** : neutralisées par le cours de référence officiel (dividendes, attributions gratuites, divisions).
- **Rendements** : logarithmiques journaliers ; features et covariance annualisées (× 252).
- **Taux sans risque** : TMM d'octobre 2026 (7 %), converti en taux continu ln(1,07) = 6,77 %.
- **Limites connues** : volumes 2026 non publiés dans les bulletins ; biais du survivant (10 sociétés radiées depuis 2023
  hors univers) ; résultats en échantillon, le test hors échantillon relève de la Phase 3.

## Usage de l'IA générative

Une partie du code et de la rédaction a été produite avec l'aide d'un assistant IA. Cet usage est déclaré
en annexe du rapport, conformément au cahier des charges.
