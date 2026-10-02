# Prototype — Pilotage territorial de l’Assistant IA

Version corrigée le 2 octobre 2026 après l’erratum transmis sur le cas pratique.

## Point méthodologique décisif

Les deux jeux avaient été intervertis dans la consigne initiale. Le prototype utilise désormais :

- **Bêta** : `assistant-ia-dinum-deploiement-au-ministere-de-leducation-nationale-en-academie` — phase janvier-juin 2026, plafonnée à 2 500 participants, données finales d’**inscription** par catégorie de personnel, désormais figées.
- **Production** : `fr-en-assistant_ia_deploiement_menjs` — série quotidienne depuis mi-juin 2026, avec compteurs cumulés de **comptes créés** et de **messages envoyés**.

Ces deux populations ne sont ni additionnées ni rapportées comme un taux de conversion. Une inscription bêta n’implique pas une connexion ; un compte créé en production n’implique pas un usage actif.

## Indicateur principal

L’exercice est structuré autour d’un indicateur principal unique : **l’intensité d’usage hebdomadaire en production**.

Pour l’académie `a` et la date `t` :

`I7_a(t) = [M_a(t) - M_a(t-7)] / ([U_a(t) + U_a(t-7)] / 2)`

avec `M` = messages cumulés et `U` = comptes créés cumulés dans le jeu de production.

### Référence et alerte

- périmètre : les mêmes 32 domaines académiques ;
- référence hebdomadaire : **médiane des 32 valeurs I7** ;
- seuil : **50 % de cette médiane**, recalculé chaque semaine ;
- signal persistant : académie strictement sous le seuil pendant **deux semaines consécutives** ;
- calculs réalisés sur les valeurs non arrondies.

À la référence du 01/10/2026, le signal persistant identifié est **Toulouse**. Il s’agit d’un signal de diagnostic et non d’un classement de performance.

## Indicateurs de contexte

Le tableau de bord affiche également :

- le nombre de comptes créés en production ;
- les messages cumulés en production ;
- les inscriptions finales à la bêta et leur ventilation par catégorie de personnel.

La bêta est utilisée uniquement comme **contexte historique**. L’ancienne trajectoire territorialisée vers 100 000 administratifs et la matrice croisant bêta/production ont été retirées : le champ `administration` appartient au jeu bêta et ne peut pas être utilisé comme compteur courant de production.

## Recommandations

Les trois recommandations de fond sont conservées :

- **Bienveillance** : diagnostic local puis accompagnement via les relais et plans académiques de formation.
- **Exigence** : évaluer temps gagné, qualité et satisfaction avec protocole avant/après et contrôle humain.
- **Ambition** : fiabiliser les données de production et documenter les usages utiles avant généralisation : utilisateurs actifs, retours, dates d’ouverture et effectifs éligibles.

## Fichiers principaux

- `dashboard.html` : tableau de bord autonome.
- `pipeline.py` : collecte, validation et calculs.
- `config/indicator.json` : règle de l’indicateur principal.
- `docs/Note Assistant IA V2 Marc MONCHY.pdf` : note synthétique mise à jour.

## Exécution

Référence fixe au 01/10/2026 :

```bash
python pipeline.py --reference
```

Collecte API :

```bash
python pipeline.py
```

Le pipeline sait reconnaître l’ancienne archive de référence dont les fichiers avaient été nommés selon les liens intervertis et les remappe avant calcul.
