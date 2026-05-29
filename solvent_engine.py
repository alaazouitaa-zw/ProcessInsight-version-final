"""
Sélection scientifique de solvants pour extraction liquide-liquide (L-L).

Critères (Handbook of Solvent Extraction / Hansen) :
  - Affinité soluté–solvant : distance de Hansen faible
  - Sélectivité : distance solvant–diluant élevée (deux phases)
  - Coefficient de partage K estimé à partir des écarts de solubilité
"""
import math

from component_catalog import COMPONENT_CATALOG

# Seuils empiriques validés en ingénierie des procédés
HANSEN_AFFINITY_MAX = 12.0      # MPa^0.5 — bonne dissolution du soluté
HANSEN_SELECTIVITY_MIN = 7.0    # MPa^0.5 — immiscibilité solvant/diluant
MIN_SCORE_VALID = 35.0


def _hansen_tuple(component):
    d = getattr(component, "hansen_d", None)
    p = getattr(component, "hansen_p", None)
    h = getattr(component, "hansen_h", None)
    if d is not None and p is not None and h is not None:
        return (float(d), float(p), float(h))
    if getattr(component, "polarity", "") == "polar":
        return (16.0, 8.0, 12.0)
    return (16.0, 0.0, 0.0)


def hansen_distance(comp_a, comp_b):
    """Distance de Hansen (4·Δd² + Δp² + Δh²)^0.5 en MPa^0.5."""
    a = _hansen_tuple(comp_a)
    b = _hansen_tuple(comp_b)
    return math.sqrt(4.0 * (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def estimate_partition_coefficient(solute, diluent, solvent, temperature_c=25.0):
    """
    Estime K = y/x à l'équilibre (phase extract / phase raffinat)
    à partir des distances de Hansen et de la température.
    """
    d_ss = hansen_distance(solute, solvent)
    d_sd = hansen_distance(diluent, solvent)
    d_sl = hansen_distance(solute, diluent)

    # K augmente quand le solvant préfère le soluté au diluant
    selectivity = max(0.1, d_sd - d_ss)
    base = math.exp(selectivity / 12.0)

    if solute.polarity == solvent.polarity:
        base *= 1.35
    elif solute.polarity != solvent.polarity and solvent.polarity == diluent.polarity:
        base *= 0.45

    # Correction température : extraction souvent à T opération
    t_factor = 1.0 + 0.002 * (float(temperature_c) - 25.0)
    k = base * t_factor

    # Borne physique raisonnable pour L-L organique
    return round(max(0.05, min(k, 80.0)), 3)


def evaluate_solvent(solute, diluent, solvent, temperature_c=25.0):
    """Score un solvant candidat et retourne validation + justification."""
    d_ss = hansen_distance(solute, solvent)
    d_sd = hansen_distance(diluent, solvent)
    k_est = estimate_partition_coefficient(solute, diluent, solvent, temperature_c)

    score = 0.0
    reasons = []
    checks = []

    # Affinité soluté–solvant
    if d_ss <= HANSEN_AFFINITY_MAX:
        aff_pts = max(0, 30 - 2.0 * d_ss)
        score += aff_pts
        checks.append({"criterion": "affinite_soluté", "ok": True, "value": round(d_ss, 2)})
        reasons.append(
            f"Affinité favorable avec le soluté ({solute.name}) : ΔHansen = {d_ss:.1f} MPa^0.5 "
            f"(seuil ≤ {HANSEN_AFFINITY_MAX})."
        )
    else:
        checks.append({"criterion": "affinite_soluté", "ok": False, "value": round(d_ss, 2)})
        reasons.append(
            f"Affinité limitée avec le soluté : ΔHansen = {d_ss:.1f} MPa^0.5 (cible ≤ {HANSEN_AFFINITY_MAX})."
        )

    # Sélectivité / séparation de phases
    if d_sd >= HANSEN_SELECTIVITY_MIN:
        sel_pts = min(30, 2.5 * (d_sd - HANSEN_SELECTIVITY_MIN) + 15)
        score += sel_pts
        checks.append({"criterion": "selectivite_phases", "ok": True, "value": round(d_sd, 2)})
        reasons.append(
            f"Immiscibilité suffisante avec le diluant ({diluent.name}) : ΔHansen = {d_sd:.1f} MPa^0.5 "
            f"(seuil ≥ {HANSEN_SELECTIVITY_MIN})."
        )
    else:
        score -= 20
        checks.append({"criterion": "selectivite_phases", "ok": False, "value": round(d_sd, 2)})
        reasons.append(
            f"Risque de phase unique ou émulsion : ΔHansen solvant–diluant = {d_sd:.1f} "
            f"(minimum {HANSEN_SELECTIVITY_MIN})."
        )

    # Polarité (règle « like dissolves like »)
    if solute.polarity == solvent.polarity:
        score += 12
        reasons.append(f"Polarités compatibles soluté/solvant ({solute.polarity}).")
    if diluent.polarity != solvent.polarity:
        score += 10
        reasons.append(
            f"Contraste de polarité solvant ({solvent.polarity}) / diluant ({diluent.polarity}) favorable."
        )
    else:
        score -= 8
        reasons.append("Même famille de polarité solvant/diluant : sélectivité réduite.")

    # K estimé
    if k_est >= 1.2:
        score += 8
        reasons.append(f"K estimé = {k_est:.2f} (extraction efficace, E = K·S/F favorable).")
    elif k_est >= 0.5:
        score += 3
        reasons.append(f"K estimé = {k_est:.2f} (extraction modérée).")
    else:
        score -= 5
        reasons.append(f"K estimé = {k_est:.2f} faible : envisager un autre solvant.")

    scientifically_valid = (
        d_ss <= HANSEN_AFFINITY_MAX + 2
        and d_sd >= HANSEN_SELECTIVITY_MIN - 1
        and score >= MIN_SCORE_VALID
        and k_est >= 0.3
    )

    return {
        "id": solvent.id,
        "name": solvent.name,
        "score": round(score, 1),
        "k_estimated": k_est,
        "hansen_solute_solvent": round(d_ss, 2),
        "hansen_diluent_solvent": round(d_sd, 2),
        "scientifically_valid": scientifically_valid,
        "checks": checks,
        "reason": " ".join(reasons),
        "solvent_class": getattr(solvent, "solvent_class", None),
    }


def rank_solvents(solute, diluent, solvent_candidates, temperature_c=25.0, top_n=5):
    """Classe les solvants par score décroissant."""
    ranked = [
        evaluate_solvent(solute, diluent, s, temperature_c)
        for s in solvent_candidates
        if s.id not in (solute.id, diluent.id)
    ]
    ranked.sort(key=lambda x: (x["scientifically_valid"], x["score"]), reverse=True)
    return ranked[:top_n]


def select_best_solvent(solute, diluent, solvent_candidates, temperature_c=25.0):
    """Retourne le meilleur solvant validé scientifiquement, ou le meilleur score."""
    ranked = rank_solvents(solute, diluent, solvent_candidates, temperature_c, top_n=10)
    if not ranked:
        return None
    for item in ranked:
        if item["scientifically_valid"]:
            return item
    return ranked[0]


def default_hansen_for_name(name):
    """Retrouve Hansen depuis le catalogue par nom."""
    for c in COMPONENT_CATALOG:
        if c["name"] == name:
            return c.get("hansen")
    return None
