# Audit méthodologique — version corrigée 02/10/2026

- Les liens bêta / production ont été remappés conformément à l’erratum.
- Production : série quotidienne `fr-en-assistant_ia_deploiement_menjs`, compteurs cumulés de comptes créés et de messages.
- Bêta : jeu figé `assistant-ia-dinum-deploiement-au-ministere-de-leducation-nationale-en-academie`, inscriptions finales par catégorie de personnel.
- Indicateur principal : I7 production = messages envoyés sur 7 jours / moyenne des comptes créés aux deux bornes.
- Référence hebdomadaire : médiane des 32 académies.
- Seuil : 50 % de la médiane, recalculé chaque semaine.
- Signal : sous le seuil pendant deux semaines consécutives.
- La bêta est uniquement un contexte historique. Elle n’est pas utilisée comme mesure d’usage ni comme compteur courant de déploiement.
- L’ancienne trajectoire territorialisée vers 100 000 administratifs et la matrice croisée sont retirées car le champ `administration` appartient au jeu bêta figé.
- Référence du 01/10/2026 : seuil 0,7660803375 ; Toulouse reste le seul signal persistant.
