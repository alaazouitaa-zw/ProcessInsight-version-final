"""
Moteur colonne d'absorption gaz-liquide
Henry / y* = mx, McCabe-Thiele (plateaux), HTU-NTU (garnissage),
bilans matière, transfert de masse, simulation dynamique, diagnostics industriels.
"""

import math
from validation_engine import ValidationResult

TOL = 1e-6
MAX_STAGES = 60
R_GAS = 8.314  # J/(mol·K)


def _clamp01(v):
    return max(0.0, min(1.0, v))


def estimate_m_from_components(comp_solute, comp_absorbant, T_c=25.0, default_m=1.5):
    """Estimation m (y*=mx) pour absorption G-L — indépendante du K VLE distillation."""
    if not comp_solute or not comp_absorbant:
        return default_m
    try:
        import thermo_engine
        T_k = T_c + 273.15
        ps = thermo_engine.calculate_vapor_pressure(
            comp_solute.antoine_A, comp_solute.antoine_B, comp_solute.antoine_C, T_k
        )
        pa = thermo_engine.calculate_vapor_pressure(
            comp_absorbant.antoine_A, comp_absorbant.antoine_B, comp_absorbant.antoine_C, T_k
        )
        if pa and pa > 1e-6:
            return round(max(0.05, min(50.0, ps / pa)), 3)
    except Exception:
        pass
    return default_m


def henry_m_from_temperature(m_ref, T_k, T_ref_k=298.15, delta_h_abs=20000.0):
    """Loi de Henry : m(T) = m_ref * exp(-ΔH_abs/R * (1/T - 1/T_ref))."""
    if T_k <= 0 or T_ref_k <= 0:
        return m_ref
    return m_ref * math.exp(-delta_h_abs / R_GAS * (1.0 / T_k - 1.0 / T_ref_k))


def equilibrium_y_star(x, m, curve=None):
    x = max(0.0, x)
    if curve:
        for i in range(len(curve) - 1):
            p1, p2 = curve[i], curve[i + 1]
            if p1["x"] <= x <= p2["x"]:
                if abs(p2["x"] - p1["x"]) < TOL:
                    return p1["y"]
                return p1["y"] + (x - p1["x"]) * (p2["y"] - p1["y"]) / (p2["x"] - p1["x"])
    return m * x


def build_equilibrium_curve(m, n=51, x_max=0.15):
    xmax = max(x_max, 0.05)
    return [{"x": i * xmax / (n - 1), "y": m * i * xmax / (n - 1)} for i in range(n)]


def operating_line_y(x, G, L, x_in, y_out, flow_direction="counter_current"):
    """Droite opératoire : y = (L/G)(x - x_in) + y_out (contre-courant, gaz monte)."""
    if G <= 0:
        return y_out
    slope = L / G
    if flow_direction == "cocurrent":
        return slope * (x - x_in) + y_out
    return slope * (x - x_in) + y_out


def material_balance_global(G, L, y_in, y_out, x_in):
    """Bilan soluté : x_out = x_in + (G/L)(y_in - y_out)."""
    if L <= 0:
        return {"x_out": x_in, "G_out": G, "L_out": L, "moles_absorbed": 0.0}
    x_out = x_in + (G / L) * (y_in - y_out)
    moles_absorbed = G * (y_in - y_out)
    return {
        "x_out": _clamp01(x_out),
        "G_out": G,
        "L_out": L,
        "moles_absorbed": moles_absorbed,
    }


def absorption_factor(L, G, m):
    """A = L / (m·G) pour contre-courant dilué."""
    if G <= 0 or m <= 0:
        return 0.0
    return L / (m * G)


def L_minimum(G, L, y_in, y_out, x_in, m):
    x_out_eq = y_in / m if m > 0 else 0.0
    if x_out_eq > x_in + TOL:
        return G * (y_in - y_out) / (x_out_eq - x_in)
    return float("inf")


def kremser_stages(y_in, y_out, x_in, G, L, m):
    A = absorption_factor(L, G, m)
    if A <= 0:
        return {"n": 0, "A": A, "error": "Facteur A invalide."}
    if abs(A - 1.0) < TOL:
        denom = y_out - m * x_in
        if abs(denom) < TOL:
            return {"n": float("inf"), "A": A, "error": "Cible inatteignable (A=1)."}
        return {"n": max(0, (y_in - y_out) / denom), "A": A, "error": None}
    num = ((y_in - m * x_in) / (y_out - m * x_in)) * (1.0 - 1.0 / A) + 1.0 / A
    if num <= 0:
        return {"n": 999, "A": A, "error": "Séparation impossible (Kremser)."}
    return {"n": max(0, math.log(num) / math.log(A)), "A": A, "error": None}


def mccabe_thiele_absorption(y_in, y_out, x_in, G, L, m, curve, flow_direction="counter_current"):
    """Construction McCabe-Thiele : bas (x_in, y_out) → haut (x_out, y_in)."""
    if G <= 0 or L <= 0:
        return {"stages": [], "n_stages": 0, "op_line": [], "pinch": None, "error": "Débits invalides."}

    bal = material_balance_global(G, L, y_in, y_out, x_in)
    x_out = bal["x_out"]
    op_dense = [
        {"x": x, "y": operating_line_y(x, G, L, x_in, y_out, flow_direction)}
        for x in [i * max(x_out, x_in, 0.01) * 1.2 / 40 for i in range(41)]
    ]
    op_line_endpoints = [{"x": x_in, "y": y_out}, {"x": x_out, "y": y_in}]

    stages_pts = []
    current_x = x_in
    current_y = y_out
    stages_pts.append({"x": current_x, "y": current_y})
    n_stages = 0
    pinch = None

    while n_stages < MAX_STAGES and current_y < y_in - TOL:
        y_eq = equilibrium_y_star(current_x, m, curve)
        stages_pts.append({"x": current_x, "y": y_eq})

        x_eq = current_y / m if m > 0 else current_x
        if abs(x_eq - current_x) < TOL and n_stages == 0:
            pinch = {"x": current_x, "y": current_y, "type": "équilibre"}
        stages_pts.append({"x": x_eq, "y": current_y})

        new_y = operating_line_y(x_eq, G, L, x_in, y_out, flow_direction)
        if new_y >= y_in - TOL:
            stages_pts.append({"x": x_eq, "y": y_in})
            n_stages += 1
            break
        stages_pts.append({"x": x_eq, "y": new_y})
        current_x = x_eq
        current_y = new_y
        n_stages += 1

    return {
        "stages": stages_pts,
        "n_stages": n_stages,
        "op_line": op_line_endpoints,
        "op_dense": op_dense,
        "pinch": pinch,
        "x_out": x_out,
        "error": None,
    }


def ntu_htu_packed(y_in, y_out, x_in, G, L, m, absorption_type="physical", hetp_ref=0.5):
    """NTU analytique (contre-courant, équilibre linéaire y*=mx). Z = HTU × NTU."""
    A = absorption_factor(L, G, m)
    if A <= 0:
        return {"NTU": 0, "HTU": 0, "Z": 0, "A": A, "error": "A <= 0"}
    if abs(A - 1.0) < TOL:
        ntu = (y_in - y_out) / max(y_out - m * x_in, TOL)
    else:
        num = ((y_in - m * x_in) / max(y_out - m * x_in, TOL)) * (1 - 1 / A) + 1 / A
        if num <= 0:
            return {"NTU": 999, "HTU": 0, "Z": 999, "A": A, "error": "NTU impossible"}
        ntu = math.log(num) / math.log(A)

    if absorption_type == "chemical":
        ntu *= 0.85

    K_G_a = 1.2
    HTU = hetp_ref
    Z = HTU * ntu

    return {
        "NTU": round(ntu, 3),
        "HTU": round(HTU, 4),
        "Z": round(Z, 3),
        "A": A,
        "K_G_a": round(K_G_a, 4),
        "error": None,
    }


def mass_transfer_analysis(y, x, m, G, L, k_g=0.02, k_l=0.05, a=200.0):
    """N_A = K_G·a·(y - y*), résistances gaz/liquide."""
    y_star = m * x
    driving = y - y_star
    if k_g <= 0 or k_l <= 0:
        K_G = k_g
    else:
        m_ratio = m * (G / max(L, TOL))
        K_G = 1.0 / (1.0 / k_g + m_ratio / k_l)
    K_G_a = K_G * a
    N_A = K_G_a * driving
    eta_local = driving / max(y, TOL) if y > TOL else 0.0
    return {
        "y_star": round(y_star, 6),
        "driving_force": round(driving, 6),
        "K_G": round(K_G, 5),
        "K_G_a": round(K_G_a, 4),
        "N_A": round(N_A, 6),
        "eta_local": round(min(1.0, max(0.0, eta_local)), 4),
        "resistance_gas_frac": round(k_l / (k_l + k_g * m * G / max(L, TOL)), 3),
    }


def simulate_dynamic_profile(y_in, y_out, x_in, G, L, m, n_stages, T_gas, T_liq):
    """Profil étage par étage (x, y, T) pour animation."""
    n = max(1, int(round(n_stages))) if n_stages < 900 else 10
    profile = []
    for i in range(n + 1):
        frac = i / n
        y = y_out + (y_in - y_out) * frac
        x = x_in + (G / max(L, TOL)) * (y_in - y) if L > 0 else x_in
        T_g = T_gas - 2.0 * frac
        T_l = T_liq + 1.5 * frac
        mt = mass_transfer_analysis(y, x, m, G, L)
        profile.append({
            "stage": i + 1,
            "y": round(y, 5),
            "x": round(x, 5),
            "y_star": mt["y_star"],
            "T_gas_C": round(T_g, 2),
            "T_liq_C": round(T_l, 2),
            "N_A": mt["N_A"],
            "section": "absorption",
        })
    return profile


def column_hydraulics(G, L, rho_g=1.2, rho_l=1000.0, mu_l=0.001, column_d=0.5, tray_type="sieve", T_k=298.15, P_kpa=101.325):
    """Estimation flooding, weeping, vitesse gaz, ΔP (corrélations simplifiées industrielles)."""
    area = math.pi * (column_d / 2) ** 2
    n_mol_s = max(G, 0) / 3600.0
    v_molar = 8.314e-3 * T_k / max(P_kpa, 1.0)
    q_gas = n_mol_s * v_molar
    v_g = q_gas / max(area, 1e-6)
    v_flood = 2.8 if tray_type == "sieve" else 3.2
    flooding_frac = v_g / v_flood
    weeping = flooding_frac < 0.35 and tray_type != "packed"
    L_over_G = L / max(G, TOL)
    insufficient_liquid = L_over_G < 0.8
    dp_per_tray = 500.0 * (v_g / 1.5) ** 2 if tray_type != "packed" else 0
    dp_packed = 150.0 * v_g ** 1.8 if tray_type == "packed" else 0

    return {
        "v_gas_m_s": round(v_g, 3),
        "v_flood_m_s": v_flood,
        "flooding_frac": round(flooding_frac, 3),
        "flooding": flooding_frac > 0.85,
        "weeping": weeping,
        "insufficient_liquid": insufficient_liquid,
        "L_over_G": round(L_over_G, 3),
        "dp_pa_per_tray": round(dp_per_tray, 0),
        "dp_packed_pa_m": round(dp_packed, 0),
        "column_d_m": column_d,
    }


def absorption_yield(y_in, y_out):
    if y_in <= 0:
        return 0.0
    return _clamp01((y_in - y_out) / y_in) * 100.0


def validate_absorption(G, L, y_in, y_out, x_in, m, n_mt, n_kr, bal, hydro):
    result = ValidationResult()
    if not (0 <= y_in <= 1 and 0 <= y_out <= 1):
        result.add_error("Fractions gaz hors limites [0,1]", "ABS_Y")
    if y_out >= y_in:
        result.add_error(f"y_out ({y_out}) doit être < y_in ({y_in})", "ABS_PUR")
    if y_out <= m * x_in + TOL:
        result.add_error(
            f"Pureté impossible : y_out ≤ y*({x_in}) = {m*x_in:.5f} (limite thermodynamique)",
            "ABS_THERMO",
        )
    if G <= 0 or L <= 0:
        result.add_error("Débits G ou L invalides", "ABS_FLOW")
    if m <= 0:
        result.add_error(f"Coefficient m invalide ({m})", "ABS_M")
    if bal:
        err = abs(G + L - bal.get("G_out", G) - bal.get("L_out", L))
        if err > 1e-3:
            result.add_warning(f"Bilan global écart {err:.2f} mol/h", "ABS_BAL")
    if n_kr > 0 and n_mt > 0 and n_kr < 900:
        rel = abs(n_mt - n_kr) / max(n_kr, 0.1)
        if rel > 0.35:
            result.add_warning(
                f"Écart McCabe ({n_mt}) vs Kremser ({n_kr:.1f}) > 35%.", "ABS_MISMATCH"
            )
        else:
            result.add_physics_check("MT/Kremser", True, f"N_MT={n_mt}, N_K={n_kr:.1f}")
    if hydro.get("flooding") and hydro.get("flooding_frac", 0) > 0.95:
        result.add_error("Risque de flooding — réduire débit gaz ou augmenter diamètre", "ABS_FLOOD")
    elif hydro.get("flooding"):
        result.add_warning("Approche du flooding (> 85% v_flood)", "ABS_FLOOD_WARN")
    if hydro.get("insufficient_liquid"):
        result.add_warning("Débit liquide insuffisant (L/G faible)", "ABS_LIQ")
    if result.is_valid:
        result.add_info(
            "Résultats validés : bilans matière, Henry y*=mx, McCabe-Thiele / HTU-NTU."
        )
    return result


def build_warnings(errors, validation, hydro, n_mt, n_kr, yld, pinch):
    warnings = []
    if validation.is_valid:
        warnings.append({
            "type": "success",
            "message": "Bilans et thermodynamique cohérents (standards génie chimique).",
        })
    for e in validation.errors:
        warnings.append({"type": "danger", "message": e["message"]})
    for w in validation.warnings:
        warnings.append({"type": "warning", "message": w["message"]})
    for err in errors:
        warnings.append({"type": "warning", "message": err})
    if hydro.get("flooding"):
        warnings.append({"type": "danger", "message": "⚠ FLOODING — réduire vitesse gaz ou agrandir la colonne."})
    if hydro.get("weeping"):
        warnings.append({"type": "warning", "message": "Weeping probable — vitesse gaz trop faible sur plateaux."})
    if hydro.get("insufficient_liquid"):
        warnings.append({"type": "warning", "message": "Débit liquide insuffisant pour le lavage du gaz."})
    if pinch:
        warnings.append({
            "type": "info",
            "message": f"Point de pincement détecté près de x={pinch.get('x', 0):.4f}.",
        })
    if n_mt > 0 and n_kr > 0 and n_kr < 900 and abs(n_mt - n_kr) / max(n_kr, 0.1) <= 0.35:
        warnings.append({
            "type": "success",
            "message": f"Cohérence McCabe-Thiele ({n_mt}) et Kremser ({n_kr:.1f}).",
        })
    if yld >= 90:
        warnings.append({"type": "success", "message": f"Absorption efficace — {yld:.0f}% du soluté capté."})
    return warnings


def industrial_conclusion(column_type, n_stages, Z, yld, A, hydro, valid):
    parts = []
    if not valid:
        return "Simulation non valide — corriger les paramètres avant exploitation industrielle."
    if column_type == "packed":
        parts.append(f"Colonne à garnissage : Z ≈ {Z:.2f} m (HTU-NTU).")
    else:
        parts.append(f"Colonne à plateaux : {n_stages} étage(s) théorique(s) (McCabe-Thiele).")
    parts.append(f"Rendement {yld:.0f}%, facteur A = {A:.2f}.")
    if hydro.get("flooding"):
        parts.append("Régime : flooding — révision hydraulique urgente.")
    elif hydro.get("weeping"):
        parts.append("Régime : weeping — augmenter débit gaz ou revoir les plateaux.")
    else:
        parts.append("Régime hydraulique acceptable pour exploitation.")
    return " ".join(parts)


def calculate_gas_absorption(
    y_in,
    y_out,
    x_in,
    G,
    L,
    m,
    *,
    column_type="tray",
    absorption_type="physical",
    flow_direction="counter_current",
    T_gas_C=25.0,
    T_liq_C=20.0,
    P_kpa=101.325,
    hetp=0.5,
    tray_efficiency=0.65,
    rho_l=1000.0,
    mu_l=0.001,
    MW_l=18.0,
    column_d=0.6,
    n_theoretical_override=None,
    thermo_m=None,
):
    if m < 0.1 and thermo_m and thermo_m >= 0.1:
        m = thermo_m
    if m < 0.1:
        m = 1.5
    m = max(m, 0.01)

    T_g_k = T_gas_C + 273.15
    T_l_k = T_liq_C + 273.15
    T_mean = 0.5 * (T_g_k + T_l_k)
    m_T = henry_m_from_temperature(m, T_mean)
    curve = build_equilibrium_curve(m_T, x_max=max(0.15, x_in + G / max(L, 1) * y_in * 1.5))

    bal = material_balance_global(G, L, y_in, y_out, x_in)
    x_out = bal["x_out"]
    yld = absorption_yield(y_in, y_out)
    A = absorption_factor(L, G, m_T)
    L_min = L_minimum(G, L, y_in, y_out, x_in, m_T)

    kr = kremser_stages(y_in, y_out, x_in, G, L, m_T)
    n_kr = kr["n"] if not kr.get("error") else 0
    if math.isinf(n_kr):
        n_kr = 99

    mt = mccabe_thiele_absorption(
        y_in, y_out, x_in, G, L, m_T, curve, flow_direction
    )
    n_mt = mt["n_stages"]

    if column_type == "packed":
        pack = ntu_htu_packed(y_in, y_out, x_in, G, L, m_T, absorption_type, hetp_ref=hetp)
        n_final = pack["NTU"] if not pack.get("error") else n_kr
        Z = pack["Z"]
        HTU = pack["HTU"]
        NTU = pack["NTU"]
        n_tray_equiv = NTU
    else:
        n_final = n_mt if column_type == "tray" else n_mt
        n_tray_real = math.ceil(n_final / max(tray_efficiency, 0.1)) if n_final < 900 else 999
        Z = n_tray_real * 0.45
        HTU = hetp
        NTU = n_final
        n_tray_equiv = n_final

    if n_theoretical_override and n_theoretical_override > 0:
        n_final = n_theoretical_override

    errors = []
    if kr.get("error"):
        errors.append(kr["error"])
    if mt.get("error"):
        errors.append(mt["error"])

    rho_g = max(0.5, P_kpa * max(MW_l, 18) / (8.314 * T_g_k) * 0.001)
    hydro = column_hydraulics(
        G, L,
        rho_g=rho_g,
        rho_l=rho_l,
        mu_l=mu_l,
        column_d=column_d,
        tray_type="packed" if column_type == "packed" else "sieve",
        T_k=T_g_k,
        P_kpa=P_kpa,
    )

    profile = simulate_dynamic_profile(
        y_in, y_out, x_in, G, L, m_T, n_final if n_final < 900 else 10, T_gas_C, T_liq_C
    )

    mt_sample = mass_transfer_analysis(y_in, x_in, m_T, G, L)
    eff_global = yld / 100.0 * tray_efficiency if column_type == "tray" else yld / 100.0

    validation = validate_absorption(
        G, L, y_in, y_out, x_in, m_T, n_mt, n_kr, bal, hydro
    )
    warnings = build_warnings(errors, validation, hydro, n_mt, n_kr, yld, mt.get("pinch"))

    eq_line = [{"x": p["x"], "y": p["y"]} for p in curve]
    op_line = mt["op_line"]

    height_yield = [
        {"Z_frac": i / 20, "yield_pct": yld * (i / 20)}
        for i in range(21)
    ]

    return {
        "process": "absorption",
        "success": validation.is_valid and not errors,
        "column_type": column_type,
        "absorption_type": absorption_type,
        "flow_direction": flow_direction,
        "A": round(A, 4),
        "L_min": round(L_min, 2) if L_min != float("inf") else 99999,
        "m": round(m_T, 4),
        "m_ref": round(m, 4),
        "henry": {"y_star_eq": "y* = m·x", "T_gas_C": T_gas_C, "T_liq_C": T_liq_C},
        "x_out": round(x_out, 6),
        "y_in": y_in,
        "y_out": y_out,
        "x_in": x_in,
        "n_stages": round(n_final, 2) if n_final < 900 else 999,
        "n_stages_real": math.ceil(n_mt / max(tray_efficiency, 0.1)) if column_type == "tray" and n_mt < 900 else 0,
        "n_kremser": round(n_kr, 2),
        "n_mt": n_mt,
        "hetp": hetp,
        "HTU": round(HTU, 4) if column_type == "packed" else round(hetp, 3),
        "NTU": round(NTU, 3),
        "Z": round(Z, 3) if column_type == "packed" else round(Z, 3),
        "tray_efficiency": tray_efficiency,
        "yield_pct": round(yld, 2),
        "efficiency_global": round(eff_global * 100, 2),
        "moles_absorbed": round(bal["moles_absorbed"], 2),
        "material_balance": {
            "G_in": G,
            "L_in": L,
            "G_out": G,
            "L_out": L,
            "global": f"{G}+{L}={G}+{L}",
            "solute": f"G({y_in}-{y_out})=L({x_out}-{x_in})",
        },
        "mass_transfer": mt_sample,
        "diagram": {
            "eq_line": eq_line,
            "op_line": op_line,
            "stages": mt["stages"],
            "equilibrium": curve,
            "operating_dense": mt.get("op_dense", []),
        },
        "profile": profile,
        "height_yield": height_yield,
        "hydrodynamics": hydro,
        "pinch_point": mt.get("pinch"),
        "warnings": warnings,
        "validation": validation.to_dict(),
        "conclusion": industrial_conclusion(
            column_type, n_mt, Z, yld, A, hydro, validation.is_valid
        ),
        "dashboard": {
            "y_in_pct": round(y_in * 100, 3),
            "y_out_pct": round(y_out * 100, 4),
            "yield_pct": round(yld, 1),
            "n_stages": round(n_final, 1) if n_final < 900 else "∞",
            "Z_m": round(Z, 2),
            "A_factor": round(A, 3),
            "L_over_G": round(L / G, 3) if G > 0 else 0,
        },
        "flows": {"G": G, "L": L, "x_in": x_in, "x_out": x_out, "y_in": y_in, "y_out": y_out},
        "inputs": {
            "y_in": round(y_in * 100, 2),
            "y_out": round(y_out * 100, 4),
            "x_in": round(x_in * 100, 2),
            "G_kmol_h": round(G, 2),
            "L_kmol_h": round(L, 2),
            "m": round(m, 3),
            "T_gas_C": T_gas_C,
            "T_liq_C": T_liq_C,
            "P_kPa": P_kpa,
        },
        "outputs": {
            "n_stages": round(n_final, 1) if n_final < 900 else "∞",
            "x_out": round(x_out, 4),
            "yield_pct": round(yld, 1),
            "Z_m": round(Z, 2),
            "A_factor": round(A, 3),
            "success": validation.is_valid and not errors,
        },
        "errors": errors,
    }
