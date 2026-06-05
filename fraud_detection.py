"""
Défi — Détection de fraude financière.

Vous devez implémenter la fonction `detect_fraud`.
La fonction `load_transactions` vous est FOURNIE (ne la modifiez pas).
"""

import csv
from datetime import datetime, timezone


def load_transactions(path):
    """Lit un fichier CSV de transactions et renvoie une liste de dicts."""
    transactions = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append(_clean_row(row))
    return transactions


def _clean_row(row):
    def get(key):
        v = row.get(key)
        return v.strip() if isinstance(v, str) and v.strip() != "" else None

    amount_raw = get("amount")
    try:
        amount = float(amount_raw) if amount_raw is not None else None
    except ValueError:
        amount = None

    card_raw = get("card_present")
    if card_raw is None:
        card_present = None
    else:
        card_present = card_raw.lower() in ("true", "1", "yes", "oui")

    return {
        "transaction_id": get("transaction_id"),
        "timestamp": get("timestamp"),
        "user_id": get("user_id"),
        "amount": amount,
        "currency": get("currency"),
        "merchant": get("merchant"),
        "country": get("country"),
        "card_present": card_present,
    }


# --- Paramètres de la logique métier (réglés pour limiter les faux positifs) ---

# Champs considérés comme indispensables pour traiter une transaction.
# (timestamp et card_present sont tolérés vides par l'énoncé.)
REQUIRED_FIELDS = ("amount", "currency", "merchant", "country", "user_id")

# Un montant est "très supérieur à l'habitude" s'il dépasse à la fois
# un multiple du montant habituel ET une marge absolue (évite de signaler
# un simple achat un peu plus cher que d'ordinaire).
HIGH_AMOUNT_FACTOR = 5.0
HIGH_AMOUNT_ABS_MARGIN = 100.0
MIN_HISTORY_FOR_AMOUNT = 2

# Deux pays différents séparés par moins de ce délai = déplacement impossible.
IMPOSSIBLE_TRAVEL_HOURS = 6

# Rafale de transactions : trop d'opérations dans une fenêtre courte.
# Plusieurs fenêtres pour couvrir aussi bien les rafales très rapides
# (test de carte) que les pics plus étalés. (minutes, nombre minimal)
BURST_RULES = ((1, 3), (10, 4))

# Doublon / rejeu : même montant et même commerçant à très peu d'intervalle.
DUPLICATE_WINDOW_MINUTES = 5

# Seuils de score par règle (alignés sur la référence du défi).
SCORE_NEGATIVE = 0.9
SCORE_HIGH_AMOUNT = 0.9
SCORE_GEO = 0.88
SCORE_MISSING = 0.85
SCORE_BURST = 0.8
SCORE_DUPLICATE = 0.8


def _to_amount(value):
    """Convertit un montant en float de façon tolérante (str, virgule…), sinon None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace(" ", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _is_blank(value):
    """True si la valeur est absente ou vide (None ou chaîne d'espaces)."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def _parse_timestamp(ts):
    """Convertit un horodatage ISO 8601 en datetime aware (UTC), ou None."""
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    dt = None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                dt = None
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _group_by_user(transactions):
    groups = {}
    for tx in transactions:
        groups.setdefault(tx.get("user_id"), []).append(tx)
    return groups


def _geo_flagged_ids(transactions):
    """Identifiants impliqués dans un changement de pays trop rapide pour être réel.

    On compare toutes les paires de transactions d'un même client (et pas
    seulement les consécutives) : ainsi une opération intercalée dans le même
    pays ne masque pas un aller-retour géographique impossible.
    """
    flagged = set()
    for user_txs in _group_by_user(transactions).values():
        located = [
            (t, _parse_timestamp(t.get("timestamp")))
            for t in user_txs
            if t.get("country")
        ]
        located = [(t, dt) for (t, dt) in located if dt is not None]
        for i, (ta, da) in enumerate(located):
            for (tb, db) in located[i + 1:]:
                if ta.get("country") != tb.get("country"):
                    gap_hours = abs((db - da).total_seconds()) / 3600.0
                    if gap_hours < IMPOSSIBLE_TRAVEL_HOURS:
                        flagged.add(id(ta))
                        flagged.add(id(tb))
    return flagged


def _burst_flagged_ids(transactions):
    """Identifiants pris dans une rafale anormale d'opérations (ex. test de carte)."""
    flagged = set()
    for user_txs in _group_by_user(transactions).values():
        located = [
            (t, _parse_timestamp(t.get("timestamp")))
            for t in user_txs
        ]
        located = [(t, dt) for (t, dt) in located if dt is not None]
        for (ti, di) in located:
            for minutes, min_count in BURST_RULES:
                window = minutes * 60.0
                count = sum(
                    1 for (_, dj) in located
                    if abs((dj - di).total_seconds()) <= window
                )
                if count >= min_count:
                    flagged.add(id(ti))
                    break
    return flagged


def _median(values):
    """Médiane d'une liste de nombres (liste supposée non vide)."""
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def _duplicate_flagged_ids(transactions):
    """Identifiants de transactions qui se répètent à l'identique trop vite.

    Même client, même commerçant et même montant (> 0) à moins de quelques
    minutes d'intervalle : signature classique d'un double débit ou d'un rejeu.
    """
    flagged = set()
    window = DUPLICATE_WINDOW_MINUTES * 60.0
    for user_txs in _group_by_user(transactions).values():
        located = []
        for t in user_txs:
            amount = _to_amount(t.get("amount"))
            dt = _parse_timestamp(t.get("timestamp"))
            if t.get("merchant") and amount is not None and amount > 0 and dt is not None:
                located.append((t, amount, dt))
        for (ta, aa, da) in located:
            for (tb, ab, db) in located:
                if ta is tb:
                    continue
                if (
                    ta.get("merchant") == tb.get("merchant")
                    and aa == ab
                    and abs((db - da).total_seconds()) <= window
                ):
                    flagged.add(id(ta))
                    flagged.add(id(tb))
    return flagged


def _user_amounts(transactions):
    """Pour chaque utilisateur, la liste de ses montants valides (> 0)."""
    amounts = {}
    for tx in transactions:
        amount = _to_amount(tx.get("amount"))
        if amount is not None and amount > 0:
            amounts.setdefault(tx.get("user_id"), []).append(amount)
    return amounts


def detect_fraud(transactions):
    """Analyse une liste de transactions et renvoie un verdict pour chacune.

    Retour : list[dict] avec transaction_id, fraud_score (0-1),
    is_suspicious (bool), reason (str) — un résultat par transaction, même ordre.

    Stratégie (du plus simple au plus fin) :
      Niveau 1 — anomalies évidentes : champs manquants, montant nul/négatif.
      Niveau 2 — logique métier : montant anormal vs historique du client,
                 incohérence géographique, fréquence (rafale) suspecte.
      Niveau 3 — finesse : marges et historique minimal pour éviter de
                 signaler à tort des transactions inhabituelles mais légitimes.
    """
    if not transactions:
        return []

    geo_flagged = _geo_flagged_ids(transactions)
    burst_flagged = _burst_flagged_ids(transactions)
    duplicate_flagged = _duplicate_flagged_ids(transactions)
    user_amounts = _user_amounts(transactions)

    results = []
    for tx in transactions:
        reasons = []  # liste de (score, raison)

        amount = _to_amount(tx.get("amount"))

        # --- Niveau 1 : champs obligatoires manquants ---
        missing = []
        for field in REQUIRED_FIELDS:
            if field == "amount":
                if amount is None:
                    missing.append("amount")
            elif _is_blank(tx.get(field)):
                missing.append(field)
        if missing:
            reasons.append(
                (SCORE_MISSING, "Champs obligatoires manquants: " + ", ".join(missing))
            )

        # --- Niveau 1 : montant nul ou négatif ---
        if amount is not None and amount <= 0:
            reasons.append((SCORE_NEGATIVE, "Montant nul ou négatif"))

        # --- Niveau 2 : montant très supérieur à l'habitude du client ---
        # On compare au montant *habituel* via la médiane des autres
        # transactions du client : robuste face à une valeur aberrante isolée
        # dans l'historique (la moyenne, elle, se laisse tirer par un outlier).
        if amount is not None and amount > 0:
            others = list(user_amounts.get(tx.get("user_id"), []))
            if amount in others:
                others.remove(amount)
            if len(others) >= MIN_HISTORY_FOR_AMOUNT:
                typical = _median(others)
                if typical > 0 and (
                    amount > HIGH_AMOUNT_FACTOR * typical
                    and amount - typical > HIGH_AMOUNT_ABS_MARGIN
                ):
                    reasons.append(
                        (SCORE_HIGH_AMOUNT,
                         "Montant très supérieur à l'habitude du client")
                    )

        # --- Niveau 2 : incohérence géographique ---
        if id(tx) in geo_flagged:
            reasons.append(
                (SCORE_GEO, "Deux pays différents en trop peu de temps")
            )

        # --- Niveau 2 : fréquence / rafale anormale ---
        if id(tx) in burst_flagged:
            reasons.append((SCORE_BURST, "Fréquence de transactions anormale"))

        # --- Niveau 3 : doublon / rejeu de transaction ---
        if id(tx) in duplicate_flagged:
            reasons.append(
                (SCORE_DUPLICATE,
                 "Transaction en double suspecte (même montant et commerçant)")
            )

        # --- Verdict : on retient la raison la plus grave ---
        if reasons:
            score, reason = max(reasons, key=lambda r: r[0])
            is_suspicious = True
        else:
            score, reason = 0.0, "Transaction conforme au profil du client"
            is_suspicious = False

        results.append({
            "transaction_id": tx.get("transaction_id"),
            "fraud_score": round(float(score), 2),
            "is_suspicious": is_suspicious,
            "reason": reason,
        })

    return results
