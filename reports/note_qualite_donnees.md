# Note qualité des données — BVMT, 02/01/2023 → 03/11/2026

**Projet Math en assurance et finance · 5INFINI · jalon semaine 2 · extraction du 04/11/2026**

## 1. Sources et date d'extraction

| Période | Source officielle | Contenu | Fichiers |
|---|---|---|---|
| 2023-2025 | Bourse de Tunis, « Historique des données » (bvmt.com.tn/sites/default/files/historiques/) | Cotations journalières de tous les titres : référence, clôture, plus haut/bas, quantité, transactions, capitaux | `histo_cotation_2023/2024/2025.zip` |
| 2023-2025 | idem | Indices journaliers (Tunindex, Tunindex20, sectoriels) | `histo_indice_2023/2024/2025.zip` |
| 2026 (02/01 → 03/11) | Bulletins officiels quotidiens de la cote (PDF) : bvmt.com.tn jusqu'au 13/04/2026, tunis-stockexchange.com ensuite | Cours de référence, ouverture, haut, bas, clôture, dernier dividende ; Tunindex | 209 bulletins, `data/raw/bulletins/manifeste_bulletins.csv` |

Extraction le 04/11/2026 ; dernière séance : 03/11/2026. Collecte : `src/collecte.py` (requêtes espacées, fichiers publics, pas de contournement ; ilboursa non utilisé car son export exige un compte).

**Limite connue** : les bulletins 2026 ne publient pas les volumes du marché principal. Pour 2026, `volume` est vide et la liquidité est mesurée par l'indicateur « au moins une transaction » (plus haut/plus bas renseignés).

## 2. Univers et filtres

- **Univers** : 75 actions cotées à la séance du 03/11/2026 (groupes 11, 12, 99). Les 10 sociétés radiées depuis 2023 (AMS, ADWYA, Cerealis, Sopat, Servicom, Electrostar, MIP, GIF-Filter, Sitex, STS) sont exclues par définition : à signaler comme **biais du survivant** dans le rapport.
- **Historique minimal (≥ 2 ans)** : aucun titre exclu. Les 75 titres sont tous présents depuis le 02/01/2023.
- **Liquidité (≥ 60 % des séances avec au moins une transaction)** : **18 titres exclus**. Ce seuil limite la part de rendements nuls, qui sous-estiment la volatilité et écrasent les corrélations. Le résultat est sensible au seuil : 60 titres à 50 %, **57 à 60 %**, 51 à 70 %, 45 à 80 %. ASSMA (59 %) est au bord du seuil.
- **Univers final : 57 titres** × 960 séances.

| Exclu (liquidité) | % séances échangées | Exclu (liquidité) | % séances échangées |
|---|---|---|---|
| PLTU | 4 % | BL | 39 % |
| BHASS | 10 % | TINV | 43 % |
| SOTEM | 10 % | UBCI | 47 % |
| SIMPA | 12 % | MAG | 48 % |
| ALKIM | 18 % | STIP | 49 % |
| AETEC (suspendue) | 23 % | UADH | 51 % |
| SITS | 25 % | HL | 56 % |
| SMD | 27 % | ASSMA | 59 % |
| AST | 32 % | SIPHA | 34 % |

## 3. Jours manquants

- **0 jour manquant** pour les 57 titres retenus : chaque titre coté figure à chaque séance, avec son cours de référence les jours sans échange.
- Le calendrier compte 960 séances (252 en 2023, 251 en 2024, 248 en 2025, 209 en 2026), identiques pour les actions et le Tunindex. Les jours absents de 2026 sont tous fériés (20/03, 09/04, 01/05, 27-28/05, 16/06, 13/08, 25/08, 15/10).
- **Séance parasite supprimée : 17/12/2025.** Elle figure dans l'archive officielle avec toutes les clôtures à 0 et un volume nul. C'est un jour férié (Fête de la Révolution), et l'ouverture du 18/12 égale la clôture du 16/12.
- Le bulletin du 04/06/2026, publié sous un nom sans date (`BO.pdf`), a été identifié par la date imprimée.

## 4. Opérations sur titres (OST) et ajustements

**Méthode.** Chaque séance a un **cours de référence** officiel, égal à la clôture de la veille, sauf quand la Bourse l'ajuste pour une OST. Dans les archives 2022-2025, la colonne OUVERTURE contient ce cours de référence ; elle égale la clôture de la veille dans 99,5 % des cas. On calcule :

- facteur f_t = référence_t / clôture_{t−1} (OST si |f_t − 1| > 0,05 %) ;
- rendement log r_t = ln(clôture_t / référence_t) : le saut mécanique est **neutralisé**, le dividende est implicitement réinvesti ;
- prix ajusté rétroactif P*_t = P_t × Π_{s>t} f_s.

**OST détectées : 228** (dont 185 sur les 57 titres retenus).

| Type | Nombre | Identification |
|---|---|---|
| Dividendes | 105 | confirmés par la colonne « dernier dividende » des bulletins |
| Dividendes probables | 104 | baisse de référence de 0 à 25 %, sans droit d'attribution |
| Attributions gratuites | 9 | droit « DA k/n jjmmaa » de l'archive, facteur théorique n/(n+k) = facteur observé (ex. BIAT DA1/7 du 29/11/2024 : 0,8750 ; TJARI DA4/21 du 30/04/2025 : 0,8400) |
| Divisions du nominal / mixtes | 4 | CIL 15/05/2023 (0,714), MPBS 15/07/2025 (0,500), DH 01/08/2025 (0,500), TRE 15/09/2026 (0,721) ; STAR 22/12/2025 : DA 7/6 combiné à une division (0,231) |
| Ajustements à la hausse | 6 | reprises de cotation, surtout de titres exclus ; un seul retenu : STA, 20/05/2025 (+1,9 %) |

**Contrôle.** Après ajustement, aucun rendement quotidien ne dépasse ±6,2 % (seuils de variation BVMT), sauf BNASS le 14/08/2025 (+7,5 %). C'est un vrai mouvement : le seuil s'applique à la référence ex-dividende.

## 5. Contrôles croisés

- Jonction archive → bulletins : référence du 02/01/2026 = clôture du 31/12/2025 pour les 75 titres.
- Tunindex fin 2025 : 13 449,95 dans l'archive, contre 13 450,0 déduit de la variation annuelle imprimée au bulletin du 02/03/2026.
- Performance annuelle du Tunindex : +13,7 % (2024), +35,1 % (2025), +38,8 % au 03/11/2026.

## 6. Points d'attention pour la suite

- La part médiane de rendements nuls reste de 27 % parmi les titres retenus (max. 61 %) : prévoir des corrélations sur rendements hebdomadaires en complément.
- Les clôtures peuvent bouger sans transaction (réservations à la hausse ou à la baisse) : on utilise `jours_echanges.csv` pour les repérer.
- Les volumes 2026 sont absents : les indicateurs de liquidité de type Amihud sont limités à 2023-2025.
