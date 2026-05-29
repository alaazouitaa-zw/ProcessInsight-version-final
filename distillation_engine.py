"""
distillation_engine.py — DistillPro Scientific Engine
======================================================
Moteur de calcul distillation rigoureux.
Méthodes : Fenske, Underwood, Gilliland, McCabe-Thiele.
Bilans matière, énergie, profils internes.
 
Références :
  - Seader & Henley, "Separation Process Principles", 3rd ed.
  - McCabe, Smith & Harriott, "Unit Operations of Chemical Engineering", 8th ed.
  - Perry's Chemical Engineers' Handbook, 8th ed.
  - Fenske, Ind. Eng. Chem. 24 (1932) 482
  - Underwood, Trans. Inst. Chem. Eng. 10 (1932) 112
  - Molokanov, Int. Chem. Eng. 12 (1972) 209
"""
 
import math
 
# ══════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════
LAMBDA_DEFAULT = 35000.0   # J/mol — chaleur latente vaporisation (ordre de grandeur)
CP_LIQUID      = 120.0     # J/(mol·K) — capacité calorifique liquide typique
 
 
# ══════════════════════════════════════════════════════════════
# 1. ÉQUILIBRE LIQUIDE-VAPEUR
# ══════════════════════════════════════════════════════════════
 
def y_eq(x: float, alpha: float) -> float:
    """
    y* = α·x / [1 + (α−1)·x]
    Ref: McCabe-Smith, Eq. 21.8
    """
    denom = 1.0 + (alpha - 1.0) * x
    if denom < 1e-12:
        return x
    return (alpha * x) / denom
 
def x_from_y(y: float, alpha: float) -> float:
    """x = y / [α − (α−1)·y]"""
    denom = alpha - (alpha - 1.0) * y
    if abs(denom) < 1e-12:
        return y
    return max(0.0, min(1.0, y / denom))
 
def build_xy_curve(alpha: float, n: int = 101) -> list:
    return [{"x": round(i/(n-1), 4), "y": round(y_eq(i/(n-1), alpha), 4)} for i in range(n)]
 
 
# ══════════════════════════════════════════════════════════════
# 2. VALIDATION DES ENTRÉES
# ══════════════════════════════════════════════════════════════
 
def validate_inputs(F, xF, xD, xB, R, alpha, q, eff) -> list:
    """
    Retourne liste de warnings/erreurs.
    """
    issues = []
 
    # Cohérence compositions
    if not (0.0 < xB < xF < xD < 1.0):
        issues.append({
            "type": "danger",
            "code": "COMP_ORDER",
            "message": f"❌ Incohérence : il faut xB ({xB}) < xF ({xF}) < xD ({xD}) < 1"
        })
    if xD - xB < 0.05:
        issues.append({
            "type": "warning",
            "code": "SMALL_SPLIT",
            "message": "⚠️ Séparation très faible (xD − xB < 0.05) — résultats peu significatifs."
        })
 
    # Alpha
    if alpha <= 1.0:
        issues.append({
            "type": "danger",
            "code": "ALPHA_LOW",
            "message": f"❌ Volatilité relative α = {alpha:.2f} ≤ 1 — séparation thermodynamiquement impossible."
        })
    elif alpha < 1.2:
        issues.append({
            "type": "warning",
            "code": "ALPHA_WARN",
            "message": f"⚠️ α = {alpha:.2f} très faible — la colonne nécessitera un très grand nombre de plateaux."
        })
 
    # Débit
    if F <= 0:
        issues.append({"type": "danger", "code": "F_ZERO", "message": "❌ Débit F doit être > 0."})
 
    # Efficacité
    if not (0.1 <= eff <= 1.0):
        issues.append({"type": "warning", "code": "EFF_RANGE", "message": f"⚠️ Efficacité {eff*100:.0f}% hors plage usuelle (10–100%)."})
 
    # q-factor
    if q < -1.0 or q > 2.0:
        issues.append({"type": "warning", "code": "Q_RANGE", "message": f"⚠️ q = {q} inhabituel (valeur typique : -0.5 à 1.5)."})
 
    return issues
 
 
# ══════════════════════════════════════════════════════════════
# 3. BILAN DE MATIÈRE
# ══════════════════════════════════════════════════════════════
 
def mass_balance(F: float, xF: float, xD: float, xB: float) -> dict:
    """
    F = D + B
    F·xF = D·xD + B·xB
    → D = F·(xF − xB) / (xD − xB)
    Ref: Seader & Henley Eq. 7.1
    """
    if abs(xD - xB) < 1e-9:
        raise ValueError("xD ≈ xB : division par zéro dans le bilan.")
 
    D = F * (xF - xB) / (xD - xB)
    B = F - D
 
    if D < 0 or B < 0:
        raise ValueError(f"Bilan donne D={D:.3f}, B={B:.3f} — vérifier xF, xD, xB.")
 
    # Vérification fermeture bilan
    lhs = F * xF
    rhs = D * xD + B * xB
    error_pct = abs(lhs - rhs) / lhs * 100.0 if lhs > 1e-9 else 0.0
 
    return {
        "F": round(F, 4),
        "D": round(D, 4),
        "B": round(B, 4),
        "xF": round(xF, 5),
        "xD": round(xD, 5),
        "xB": round(xB, 5),
        "F_light": round(F * xF, 4),
        "D_light": round(D * xD, 4),
        "B_light": round(B * xB, 4),
        "F_heavy": round(F * (1-xF), 4),
        "D_heavy": round(D * (1-xD), 4),
        "B_heavy": round(B * (1-xB), 4),
        "balance_error_pct": round(error_pct, 6),
        "balance_ok": error_pct < 0.01,
    }
 
 
# ══════════════════════════════════════════════════════════════
# 4. FENSKE — Nmin à reflux total
# ══════════════════════════════════════════════════════════════
 
def fenske_nmin(xD: float, xB: float, alpha: float) -> dict:
    """
    Nmin = ln[(xD/(1−xD)) · ((1−xB)/xB)] / ln(α)
    Ref: Fenske, Ind. Eng. Chem. 24 (1932) 482
         Seader & Henley Eq. 9.5
    """
    if alpha <= 1.0:
        raise ValueError("α doit être > 1.")
    eps = 1e-6
    xD = max(eps, min(1-eps, xD))
    xB = max(eps, min(1-eps, xB))
 
    ratio_D = xD / (1.0 - xD)
    ratio_B = (1.0 - xB) / xB
    Nmin = math.log(ratio_D * ratio_B) / math.log(alpha)
 
    return {
        "Nmin": round(max(1.0, Nmin), 2),
        "ratio_D": round(ratio_D, 4),
        "ratio_B": round(ratio_B, 4),
        "formula": f"Nmin = ln({ratio_D:.3f} × {ratio_B:.3f}) / ln({alpha:.3f}) = {Nmin:.3f}",
    }
 
 
# ══════════════════════════════════════════════════════════════
# 5. UNDERWOOD — Rmin
# ══════════════════════════════════════════════════════════════
 
def underwood_rmin(xF: float, xD: float, alpha: float, q: float) -> dict:
    """
    Résout : α·xF/(α−θ) + (1−xF)/(1−θ) = 1−q  pour θ ∈ ]1, α[
    Puis : Rmin = α·xD/(α−θ) + (1−xD)/(1−θ) − 1
    Ref: Underwood, Trans. Inst. Chem. Eng. 10 (1932) 112
         Seader & Henley Section 9.4
    """
    target = 1.0 - q
    eps = 1e-9
 
    def f(theta):
        d1 = alpha - theta
        d2 = 1.0 - theta
        if abs(d1) < eps or abs(d2) < eps:
            return 1e15
        return (alpha * xF) / d1 + (1.0 - xF) / d2
 
    # Bisection dans ]1+ε, α−ε[
    lo, hi = 1.0 + 1e-5, alpha - 1e-5
    for _ in range(300):
        mid = (lo + hi) / 2.0
        val = f(mid)
        if abs(val - target) < 1e-8:
            break
        if val > target:
            lo = mid
        else:
            hi = mid
    theta = (lo + hi) / 2.0
 
    d1, d2 = alpha - theta, 1.0 - theta
    if abs(d1) < eps or abs(d2) < eps:
        Rmin = 0.5
    else:
        Vmin_D = (alpha * xD) / d1 + (1.0 - xD) / d2
        Rmin = max(0.01, Vmin_D - 1.0)
 
    return {
        "Rmin": round(Rmin, 4),
        "theta": round(theta, 6),
        "formula": f"θ = {theta:.4f} → Vmin/D = {Rmin+1:.4f} → Rmin = {Rmin:.4f}",
    }
 
 
# ══════════════════════════════════════════════════════════════
# 6. GILLILAND — Corrélation N vs R
# ══════════════════════════════════════════════════════════════
 
def gilliland_n(Nmin: float, Rmin: float, R: float) -> dict:
    """
    X = (R − Rmin)/(R + 1)
    Y = 1 − exp[(1+54.4X)/(11+117.2X) · (X−1)/X^0.5]   [Molokanov, 1972]
    N = (Nmin + Y) / (1 − Y)
    Ref: Seader & Henley Eq. 9.10
    """
    if R <= Rmin:
        # On force R = 1.01·Rmin pour éviter l'échec
        R = Rmin * 1.01
 
    X = (R - Rmin) / (R + 1.0)
    X = max(1e-9, X)
 
    exp_arg = ((1.0 + 54.4 * X) / (11.0 + 117.2 * X)) * ((X - 1.0) / math.sqrt(X))
    Y = 1.0 - math.exp(exp_arg)
    Y = max(0.0, min(0.999, Y))
 
    if abs(1.0 - Y) < 1e-9:
        N = Nmin * 15.0
    else:
        N = (Nmin + Y) / (1.0 - Y)
 
    N = max(Nmin + 1, N)
 
    return {
        "N": round(N, 2),
        "N_int": max(2, math.ceil(N)),
        "X": round(X, 5),
        "Y": round(Y, 5),
        "formula": f"X={X:.4f} → Y={Y:.4f} → N={N:.2f} → ceil={math.ceil(N)}",
    }
 
 
# ══════════════════════════════════════════════════════════════
# 7. McCABE-THIELE — Construction des étages
# ══════════════════════════════════════════════════════════════
 
def mccabe_thiele(xF, xD, xB, R, q, alpha, eff=0.70, N_override=None) -> dict:
    """
    Construction McCabe-Thiele complète avec profils internes.
    Droite rectification : y = (R/(R+1))·x + xD/(R+1)
    q-line              : x = xF si q=1, sinon y = q/(q-1)·x − xF/(q-1)
    Droite épuisement   : par (xB,xB) et intersection q-line/rectification
    Ref: McCabe & Thiele, Ind. Eng. Chem. 17 (1925) 605
    """
    # ── Courbe d'équilibre (haute résolution) ──
    xy_curve = build_xy_curve(alpha, 501)
 
    # ── Droite rectification ──
    sR = R / (R + 1.0)
    iR = xD / (R + 1.0)
 
    def y_rect(x):
        return sR * x + iR
 
    # ── Intersection q-line / rectification (point de pincement potentiel) ──
    if abs(q - 1.0) < 1e-5:
        x_int = xF
        y_int = y_rect(xF)
    else:
        sq = q / (q - 1.0)
        iq = -xF / (q - 1.0)
        denom = sq - sR
        if abs(denom) < 1e-10:
            x_int, y_int = xF, y_rect(xF)
        else:
            x_int = (iR - iq) / denom
            y_int = y_rect(x_int)
 
    x_int = max(xB + 0.001, min(xD - 0.001, x_int))
    y_int = max(0.0, min(1.0, y_int))
 
    # ── Droite épuisement : passe par (xB, xB) et (x_int, y_int) ──
    if abs(x_int - xB) < 1e-9:
        sE, iE = 1.0, 0.0
    else:
        sE = (y_int - xB) / (x_int - xB)
        iE = xB - sE * xB
 
    def y_strip(x):
        v = sE * x + iE
        return max(0.0, min(1.0, v))
 
    def y_op(x):
        if x >= x_int:
            return max(0.0, min(1.0, y_rect(x)))
        return y_strip(x)
 
    # ── Interpolation inverse sur la courbe d'équilibre ──
    def x_from_y_curve(y_target):
        """Cherche x sur la courbe y_eq(x)=y_target par interpolation."""
        best_x = x_from_y(y_target, alpha)  # valeur analytique directe
        return max(0.0, min(1.0, best_x))
 
    # ── Construction des marches ──
    stages_graphics = []   # pour le diagramme McCabe
    profile = []           # par étage : temp, x, y, L, V
    step_count = 0
    feed_stage = None
    current_x = xD
    current_y = xD
    MAX = 120
 
    stages_graphics.append({"x": round(current_x, 5), "y": round(current_y, 5)})
 
    for step in range(MAX):
        # 1. Aller horizontalement sur la courbe d'équilibre
        x_eq = x_from_y_curve(current_y)
        stages_graphics.append({"x": round(x_eq, 5), "y": round(current_y, 5)})
 
        section = "Rectification" if x_eq >= x_int else "Épuisement"
 
        # Détecter le plateau d'alimentation
        if feed_stage is None and x_eq < x_int:
            feed_stage = step_count + 1
 
        step_count += 1
 
        # Profil interne (L, V dépendent de la section)
        L_flow  = R * 1.0          # normalisé par D=1
        V_flow  = (R + 1.0)
        Lp_flow = L_flow + q       # section épuisement
        Vp_flow = V_flow - (1 - q)
 
        L_used = L_flow  if section == "Rectification" else Lp_flow
        V_used = V_flow  if section == "Rectification" else Vp_flow
 
        profile.append({
            "stage":   step_count,
            "section": section,
            "x":       round(x_eq, 5),
            "y":       round(current_y, 5),
            "temp":    None,    # rempli plus bas
            "L":       round(L_used, 3),
            "V":       round(V_used, 3),
        })
 
        # Critère d'arrêt
        if x_eq <= xB + 1e-4:
            stages_graphics.append({"x": round(xB, 5), "y": round(y_op(xB), 5)})
            break
 
        # 2. Aller verticalement sur la droite opératoire
        y_new = y_op(x_eq)
        stages_graphics.append({"x": round(x_eq, 5), "y": round(y_new, 5)})
        current_x = x_eq
        current_y = y_new
 
        if current_y <= xB + 1e-4:
            break
 
    if feed_stage is None:
        feed_stage = max(1, step_count // 2)
 
    # ── Nombre de plateaux réels ──
    N_real = max(1, math.ceil(step_count / eff))
 
    return {
        "N_steps":     step_count,
        "N_real":      N_real,
        "feed_stage":  feed_stage,
        "stages_graphics": stages_graphics,
        "profile":     profile,
        "lines": {
            "rectifying": [{"x": round(xD, 5), "y": round(xD, 5)},
                           {"x": round(x_int, 5), "y": round(y_int, 5)}],
            "stripping":  [{"x": round(xB, 5), "y": round(xB, 5)},
                           {"x": round(x_int, 5), "y": round(y_int, 5)}],
            "q_line":     _build_q_line(xF, q, x_int, y_int),
        },
        "x_int": round(x_int, 5),
        "y_int": round(y_int, 5),
        "sR": round(sR, 5),
        "iR": round(iR, 5),
        "sE": round(sE, 5),
        "iE": round(iE, 5),
    }
 
def _build_q_line(xF, q, x_int, y_int):
    if abs(q - 1.0) < 1e-5:
        # Verticale x = xF
        return [{"x": round(xF, 5), "y": 0.0},
                {"x": round(xF, 5), "y": round(y_int * 1.05, 5)}]
    else:
        sq = q / (q - 1.0)
        iq = -xF / (q - 1.0)
        x0 = xF
        y0 = sq * x0 + iq
        return [{"x": round(x0, 5), "y": round(y0, 5)},
                {"x": round(x_int, 5), "y": round(y_int, 5)}]
 
 
# ══════════════════════════════════════════════════════════════
# 8. PROFIL DE TEMPÉRATURE
# ══════════════════════════════════════════════════════════════
 
def compute_temperature_profile(profile: list, T_feed: float, P: float,
                                 comp1=None, comp2=None) -> list:
    """
    Calcule T par étage via interpolation linéaire entre T_bulle(xD) et T_bulle(xB).
    Si données Antoine disponibles, utilise le point de bulle réel.
    Ref: Seader & Henley, Section 10.
    """
    if not profile:
        return profile
 
    n = len(profile)
    x_vals = [s["x"] for s in profile]
 
    # Températures d'ébullition corps purs
    if comp1 and comp2:
        try:
            from thermo_engine import calculate_vapor_pressure
            import math
 
            def T_bubble_pure(comp, P_kpa):
                # Antoine inversé : T = B/(A - log10(P/0.133322)) - C
                log_P = math.log10(P_kpa / 0.133322)
                return comp.antoine_B / (comp.antoine_A - log_P) - comp.antoine_C
            T_D = T_bubble_pure(comp1, P)   # T à x=1 (composant léger)
            T_B = T_bubble_pure(comp2, P)   # T à x=0 (composant lourd)
        except:
            T_D = T_feed - 15.0
            T_B = T_feed + 25.0
    else:
        T_D = T_feed - 15.0
        T_B = T_feed + 25.0
 
    for i, s in enumerate(profile):
        x = s["x"]
        # Interpolation linéaire (approximation)
        T_i = T_B - x * (T_B - T_D)
        profile[i]["temp"] = round(T_i, 2)
 
    return profile
 
 
# ══════════════════════════════════════════════════════════════
# 9. BILAN ÉNERGÉTIQUE
# ══════════════════════════════════════════════════════════════
 
def energy_balance(D: float, B: float, F: float, R: float, q: float,
                    T_feed: float, lambda_J_mol: float = LAMBDA_DEFAULT) -> dict:
    """
    QC = (R+1)·D·λ   [condenseur total]
    QR = QC + F·(1−q)·λ  [bilan global colonne]
    Unités : D, B, F en kmol/h → conversion en mol/s
    Ref: Smith, "Chemical Process Design", Ch. 11
    """
    # kmol/h → mol/s
    D_mols = D * 1000.0 / 3600.0
    F_mols = F * 1000.0 / 3600.0
    V_mols = (R + 1.0) * D_mols    # débit vapeur section rectification
 
    QC = V_mols * lambda_J_mol / 1000.0   # kW
    # Bilan entalpique simplifié
    QR = QC + F_mols * (1.0 - q) * lambda_J_mol / 1000.0
 
    QC = max(0.0, QC)
    QR = max(0.0, QR)
 
    # Consommation spécifique
    Q_spec = (QC + QR) / D_mols / 3.6 if D_mols > 0 else 0  # kJ/kmol
 
    # Rendement (ratio énergie théorique séparation / énergie fournie)
    Q_min = F_mols * lambda_J_mol * abs(q - 0.5) / 1000.0
    rend = min(99.0, Q_min / QR * 100.0) if QR > 0 else 0.0
 
    return {
        "Q_condenser":     round(QC, 2),
        "Q_reboiler":      round(QR, 2),
        "Q_total":         round(QC + QR, 2),
        "Q_specific":      round(Q_spec, 1),
        "thermal_efficiency": round(rend, 1),
        "V_flow":          round(V_mols * 3600.0 / 1000.0, 3),  # kmol/h
        "lambda_used":     lambda_J_mol,
    }
 
 
# ══════════════════════════════════════════════════════════════
# 10. Q-FACTOR INTERPRETER
# ══════════════════════════════════════════════════════════════
 
def interpret_q(q: float) -> dict:
    """Interpréter le q-factor et retourner l'état thermique."""
    if q > 1.0:
        state = "Liquide sous-refroidi"
        color = "#60a5fa"
        badge = "SOUS-REFROIDI"
        explanation = (f"q = {q:.2f} > 1 : l'alimentation est un liquide en-dessous de sa température de bulle. "
                       f"La colonne doit fournir {(q-1)*100:.0f}% d'énergie supplémentaire pour vaporiser l'alimentation.")
    elif abs(q - 1.0) < 0.01:
        state = "Liquide saturé"
        color = "#10b981"
        badge = "LIQUIDE SAT."
        explanation = "q = 1 : l'alimentation arrive exactement à sa température de bulle. C'est la condition la plus courante."
    elif 0.01 < q < 0.99:
        state = f"Mélange liquide-vapeur (ψ = {1-q:.0%} vapeur)"
        color = "#f59e0b"
        badge = "MIXTE L+V"
        explanation = (f"q = {q:.2f} : {(1-q)*100:.0f}% de l'alimentation est déjà vaporisé. "
                       f"La q-line a une pente positive q/(q-1) = {q/(q-1):.2f}.")
    elif abs(q) < 0.01:
        state = "Vapeur saturée"
        color = "#f87171"
        badge = "VAPEUR SAT."
        explanation = "q = 0 : l'alimentation arrive exactement à son point de rosée."
    else:
        state = "Vapeur surchauffée"
        color = "#ef4444"
        badge = "SURCHAUFFÉE"
        explanation = (f"q = {q:.2f} < 0 : la vapeur est surchauffée. "
                       f"Le condenseur de tête doit absorber {abs(q)*100:.0f}% d'énergie supplémentaire.")
 
    return {
        "q": round(q, 4),
        "state": state,
        "color": color,
        "badge": badge,
        "explanation": explanation,
        "q_line_slope": round(q / (q - 1.0), 4) if abs(q - 1.0) > 0.01 else float('inf'),
    }
 
 
# ══════════════════════════════════════════════════════════════
# 11. GÉNÉRATION WARNINGS IA
# ══════════════════════════════════════════════════════════════
 
def generate_ai_warnings(R: float, Rmin: float, Nmin: float, N: float,
                          alpha: float, xD: float, xB: float, q: float) -> list:
    warnings = []
    ratio = R / Rmin if Rmin > 0 else 999.0
 
    if ratio < 1.05:
        warnings.append({"type": "danger",
                         "message": f"🚨 REFLUX INSUFFISANT : R/Rmin = {ratio:.2f} < 1.05 — la séparation est quasi-impossible. Augmenter R ≥ {Rmin*1.2:.2f}."})
    elif ratio < 1.2:
        warnings.append({"type": "warning",
                         "message": f"⚠️ Reflux proche du minimum (R/Rmin = {ratio:.2f}). Recommandation : R/Rmin ∈ [1.2, 1.5]."})
    elif ratio > 3.0:
        saving = (1.0 - 1.3/ratio)*100
        warnings.append({"type": "info",
                         "message": f"💡 Reflux élevé (R/Rmin = {ratio:.1f}) — réduction possible de {saving:.0f}% d'énergie en descendant à R/Rmin = 1.3."})
    else:
        warnings.append({"type": "success",
                         "message": f"✅ Rapport de reflux optimal : R/Rmin = {ratio:.2f} ∈ [1.2, 3.0]."})
 
    if alpha < 1.5:
        warnings.append({"type": "warning",
                         "message": f"⚠️ Volatilité faible (α = {alpha:.2f}) — colonne de grande hauteur. Envisager distillation azéotropique ou extractive."})
 
    if N > 60:
        warnings.append({"type": "warning",
                         "message": f"⚠️ Nombre d'étages élevé (N = {N:.0f}) — vérifier la faisabilité économique."})
 
    if xD > 0.99:
        warnings.append({"type": "info",
                         "message": "💡 Haute pureté distillat (xD > 0.99) — le coût marginal d'une purification supplémentaire est exponentiel."})
 
    if q > 1.2:
        warnings.append({"type": "info",
                         "message": f"💡 Alimentation sous-refroidie (q = {q:.2f}) — préchauffer l'alimentation jusqu'à ébullition permettrait d'économiser de l'énergie au rebouilleur."})
 
    return warnings
 
 
# ══════════════════════════════════════════════════════════════
# 12. FONCTION PRINCIPALE — CALCUL COMPLET
# ══════════════════════════════════════════════════════════════
 
def run_full_distillation(F: float, xF: float, xD: float, xB: float,
                           R: float, alpha: float, q: float,
                           eff: float = 0.70,
                           T_feed: float = 80.0,
                           P: float = 101.325,
                           lambda_override: float = None,
                           comp1=None, comp2=None) -> dict:
    """
    Calcul complet de la colonne de distillation.
    Retourne un dict compatible avec results.op_results.distillation dans simulation.html.
    """
    # 0. Validation
    val_issues = validate_inputs(F, xF, xD, xB, R, alpha, q, eff)
    critical = any(i["type"] == "danger" for i in val_issues)
 
    lam = lambda_override if lambda_override else LAMBDA_DEFAULT
 
    # Résultats par défaut si problème critique
    if critical:
        return {
            "error": True,
            "success": False,
            "validation_issues": val_issues,
            "warnings": val_issues,
            "N_steps": 0, "N_real": 0, "N_min": 0, "R_min": 0,
            "n_stages": 0,
            "feed_stage": 0,
            "flows": {"F": F, "D": 0, "B": 0},
            "lines": {
                "rectifying": [{"x": xD, "y": xD}, {"x": xF, "y": xF}],
                "stripping":  [{"x": xB, "y": xB}, {"x": xF, "y": xF}],
                "q_line":     [{"x": xF, "y": 0}, {"x": xF, "y": 1}],
            },
            "profile": [],
            "xy_curve": build_xy_curve(alpha),
            "energy": {"Q_condenser": 0, "Q_reboiler": 0, "Q_total": 0,
                       "Q_specific": 0, "thermal_efficiency": 0, "V_flow": 0},
            "stages_graphics": [],
            "dashboard": {"n_stages": 0},
            "q_info": interpret_q(q),
            "inputs": {
                "F_kmol_h": round(F, 2),
                "x_feed": round(xF, 4),
                "x_d": round(xD, 4),
                "x_b": round(xB, 4),
                "R": round(R, 3),
                "q": round(q, 3),
            },
            "outputs": {
                "n_stages": 0,
                "N_min": 0,
                "R_min": 0,
                "success": False,
            },
        }
 
    # 1. Bilan matière
    mb = mass_balance(F, xF, xD, xB)
    D, B = mb["D"], mb["B"]
 
    # 2. Fenske
    fk = fenske_nmin(xD, xB, alpha)
    Nmin = fk["Nmin"]
 
    # 3. Underwood
    uw = underwood_rmin(xF, xD, alpha, q)
    Rmin = uw["Rmin"]
 
    # 4. Vérification R >= Rmin
    if R <= Rmin:
        R_used = Rmin * 1.05
        val_issues.append({
            "type": "warning",
            "code": "R_ADJUSTED",
            "message": f"⚠️ R ({R:.3f}) ≤ Rmin ({Rmin:.3f}) — ajusté à R = {R_used:.3f} pour le calcul."
        })
    else:
        R_used = R
 
    # 5. Gilliland
    gl = gilliland_n(Nmin, Rmin, R_used)
    N_gilliland = gl["N"]
 
    # 6. McCabe-Thiele
    mt = mccabe_thiele(xF, xD, xB, R_used, q, alpha, eff=eff)
    N_steps  = mt["N_steps"]
    N_real   = mt["N_real"]
    feed_stg = mt["feed_stage"]
 
    # 7. Profil de température
    profile = compute_temperature_profile(mt["profile"], T_feed, P, comp1, comp2)
 
    # 8. Débits internes réels (en kmol/h)
    L_rect  = R_used * D
    V_rect  = (R_used + 1.0) * D
    L_strip = L_rect + q * F
    V_strip = V_rect - (1.0 - q) * F
 
    for s in profile:
        if s["section"] == "Rectification":
            s["L"] = round(L_rect, 3)
            s["V"] = round(V_rect, 3)
        else:
            s["L"] = round(L_strip, 3)
            s["V"] = round(V_strip, 3)
 
    # 9. Énergie
    en = energy_balance(D, B, F, R_used, q, T_feed, lambda_J_mol=lam)
 
    # 10. Q-factor
    q_info = interpret_q(q)
 
    # 11. Warnings IA
    ai_w = generate_ai_warnings(R_used, Rmin, Nmin, N_steps, alpha, xD, xB, q)
    all_warnings = val_issues + ai_w
 
    # 12. Dashboard KPIs
    recovery_light = (D * xD) / (F * xF) * 100.0 if F * xF > 0 else 0.0
    sep_factor = (xD / (1 - xD)) / (xB / (1 - xB)) if (1-xD) > 0 and xB > 0 else 0.0
 
    # 13. Courbe x-y pour le tracé
    xy_curve = build_xy_curve(alpha, 101)
 
    # 14. Inputs/Outputs pour les templates
    inputs_dict = {
        "F_kmol_h": round(F, 2),
        "x_feed": round(xF, 4),
        "x_d": round(xD, 4),
        "x_b": round(xB, 4),
        "R": round(R_used, 3),
        "q": round(q, 3),
        "alpha": round(alpha, 2),
        "T_C": round(T_feed, 1),
        "P_kPa": round(P, 2),
        "tray_eff": round(eff * 100, 1),
    }
    
    outputs_dict = {
        "n_stages": N_real,
        "N_min": round(Nmin, 2),
        "R_min": round(Rmin, 4),
        "success": not critical,
        "D_kmol_h": round(D, 3),
        "B_kmol_h": round(B, 3),
        "N_steps": N_steps,
        "N_real": N_real,
        "recovery_light_pct": round(recovery_light, 1),
        "sep_factor": round(sep_factor, 1),
    }
 
    return {
        "error": False,
        "success": not critical,
        "validation_issues": val_issues,
 
        # McCabe résultats
        "N_steps":    N_steps,
        "N_real":     N_real,
        "N_min":      round(Nmin, 2),
        "N_gilliland": round(N_gilliland, 1),
        "R_min":      round(Rmin, 4),
        "R_used":     round(R_used, 4),
        "R_ratio":    round(R_used / Rmin, 3) if Rmin > 0 else 0,
        "feed_stage": feed_stg,
 
        # Bilan matière
        "mass_balance": mb,
        "flows": {
            "F": round(F, 3), "D": round(D, 4), "B": round(B, 4),
            "L_rect": round(L_rect, 3), "V_rect": round(V_rect, 3),
            "L_strip": round(L_strip, 3), "V_strip": round(V_strip, 3),
        },
 
        # Lignes pour tracé Plotly
        "lines": mt["lines"],
        "stages_graphics": mt["stages_graphics"],
        "xy_curve": xy_curve,
        "x_int": mt["x_int"],
        "y_int": mt["y_int"],
 
        # Profil par plateau
        "profile": profile,
 
        # Énergie
        "energy": en,
 
        # Formules pédagogiques
        "fenske":    fk,
        "underwood": uw,
        "gilliland": gl,
 
        # Q-factor
        "q_info": q_info,
 
        # Dashboard
        "dashboard": {
            "xD_pct":           round(xD * 100, 2),
            "xB_pct":           round(xB * 100, 2),
            "recovery_light":   round(recovery_light, 1),
            "sep_factor":       round(sep_factor, 1),
            "R_Rmin_ratio":     round(R_used / Rmin, 3) if Rmin > 0 else 0,
            "n_stages":         N_real,
        },
 
        # Inputs/Outputs pour templates
        "inputs": inputs_dict,
        "outputs": outputs_dict,
        
        # Warnings & IA
        "warnings": all_warnings,
    }


# ══════════════════════════════════════════════════════════════
# 13. FONCTIONS ALIAS POUR COMPATIBILITÉ
# ══════════════════════════════════════════════════════════════

def calculate_distillation_advanced(F_flow: float, x_f: float, x_d: float, x_b: float,
                                    R: float, q: float, P_kpa: float = 101.325,
                                    comp1=None, comp2=None, model_type: str = None,
                                    tray_eff: float = 0.70, alpha: float = None,
                                    T_feed: float = 80.0, lambda_override: float = None) -> dict:
    """
    Alias pour run_full_distillation, compatible avec les appels dans app.py.
    Calcule automatiquement alpha à partir des composants si possible.
    """
    # Si alpha n'est pas fourni, le calculer à partir des composants
    if alpha is None:
        alpha = _calculate_alpha_from_components(comp1, comp2, x_f, T_feed, P_kpa, model_type)
    
    result = run_full_distillation(
        F=F_flow,
        xF=x_f,
        xD=x_d,
        xB=x_b,
        R=R,
        alpha=alpha,
        q=q,
        eff=tray_eff,
        T_feed=T_feed,
        P=P_kpa,
        lambda_override=lambda_override,
        comp1=comp1,
        comp2=comp2
    )
    
    # Ajouter les champs de compatibilité avec les templates
    result["success"] = not result.get("error", True)
    result["n_stages"] = result.get("N_real", 0)  # Pour compatibility avec templates
    result["N_stages"] = result.get("N_real", 0)  # Autre variante
    
    return result


def _calculate_alpha_from_components(comp1, comp2, x_f: float, T_feed: float, P_kpa: float,
                                     model_type: str = None) -> float:
    """
    Calcule la volatilité relative alpha à partir des données des composants.
    α = K1 / K2 = (y1/x1) / (y2/x2)
    """
    if comp1 is None or comp2 is None:
        return 2.5  # Valeur par défaut
    
    try:
        # Importer thermo_engine pour utiliser ses fonctions
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        import thermo_engine
        
        # Calculer les propriétés thermodynamiques
        data = thermo_engine.calculate_science_matrices(
            model_type or "Raoult (Gaz Parfait)",
            x_f, T_feed, P_kpa, comp1, comp2, None
        )
        
        # alpha est directement calculée dans calculate_science_matrices
        alpha = data.get("alpha", 2.5)
        
        # Assurer que alpha est raisonnable (entre 1.01 et 100)
        return max(1.01, min(100.0, alpha))
    except Exception:
        # En cas d'erreur, retourner une valeur par défaut raisonnable
        return 2.5


def calculate_q_properties(q: float, x_f: float, comp1=None, comp2=None,
                          P_kpa: float = 101.325, model_type: str = None) -> dict:
    """
    Retourne les propriétés du q-factor.
    Alias pour interpret_q avec paramètres élargis pour compatibilité.
    """
    return interpret_q(q)
 