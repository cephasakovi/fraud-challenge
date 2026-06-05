# Approche — `detect_fraud`

Détecteur de fraude par **règles métier explicables**, conçu pour signaler les
opérations à risque **sans accabler les clients honnêtes** (priorité forte à la
réduction des faux positifs, cf. Niveau 3).

## Principe

Pour chaque transaction, on évalue plusieurs signaux. On retient **le motif le
plus grave** (score le plus élevé) ; `is_suspicious` est vrai dès qu'au moins un
signal se déclenche. Chaque verdict est accompagné d'une **justification lisible**.

L'analyse se fait sur **tout le lot** : chaque opération est comparée à
l'historique de son client (montant habituel, déplacements, fréquence).

## Signaux implémentés

| Niveau | Signal | Déclencheur | Score |
|--------|--------|-------------|-------|
| 1 | Champs obligatoires manquants | `amount`, `currency`, `merchant`, `country`, `user_id` vide | 0.85 |
| 1 | Montant nul ou négatif | `amount <= 0` | 0.90 |
| 2 | Montant très supérieur à l'habitude | `montant > 5 × médiane` du client **et** écart absolu > 100 | 0.90 |
| 2 | Incohérence géographique | deux pays différents à moins de 6 h (toutes paires) | 0.88 |
| 2 | Fréquence anormale | ≥ 3 opérations en 1 min **ou** ≥ 4 en 10 min | 0.80 |
| 3 | Doublon / rejeu | même client, commerçant et montant à < 5 min | 0.80 |

## Choix anti faux positifs

- **Médiane** (et non moyenne) du montant habituel : robuste à une grosse dépense
  isolée dans l'historique.
- **Double condition** sur le montant (multiplicateur *et* marge absolue) : un
  achat un peu plus cher que d'ordinaire n'est pas signalé.
- **Historique minimal** requis (≥ 2 opérations) avant de juger un montant.
- **Délai de voyage plausible toléré** : deux pays espacés de plusieurs heures
  (ex. un vol long-courrier) ne sont pas signalés.

## Robustesse

- Aucune exception sur données imparfaites (champs manquants, montants invalides,
  horodatages absents ou désordonnés, doublons).
- Horodatages ISO 8601 (`Z`/offsets) normalisés en UTC ; valeurs illisibles
  ignorées pour les règles temporelles plutôt que de faire planter l'analyse.

## Vérification

- `pytest tests/` : 11/11 tests publics.
- Sortie **identique** à la référence `data/sample_expected.json` (scores,
  verdicts et formulations).

## Réglages

Tous les seuils sont des constantes en tête de `fraud_detection.py`, faciles à
ajuster selon la tolérance au risque.
