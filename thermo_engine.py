import math

def calculate_vapor_pressure(A, B, C, T_C):
    try:
        log_P = A - (B / (T_C + C))
        return round(10 ** log_P * 0.133322, 4)
    except:
        return 0.001

def get_z_factor(P_sys, T, Tc, Pc):
    # Estimation PR Z-factor simplifié (Vapeur Cubique basique)
    if not Tc or not Pc or P_sys < 500: return 1.0
    Tr = (T + 273.15) / Tc
    Pr = P_sys / Pc

def calc_gamma_uniquac(x1, x2, x3=0):
    g1 = 1.0 + (x2)**2 * 1.5 + (x3)**2 * 0.5
    g2 = 1.0 + (x1)**2 * 1.5 + (x3)**2 * 0.2
    g3 = 1.0 + (x1)**2 * 0.5 + (x2)**2 * 0.2
    return g1, g2, g3

def calc_gamma_unifac(x1, x2, x3=0):
    g1 = 1.0 + (x2)**2 * 1.8 + (x3)**2 * 0.8
    g2 = 1.0 + (x1)**2 * 1.8 + (x3)**2 * 0.4
    g3 = 1.0 + (x1)**2 * 0.8 + (x2)**2 * 0.4
    return g1, g2, g3

def get_activity(model, x1, x2, x3=0):
    if "UNIQUAC" in model or model == "NRTL": return calc_gamma_uniquac(x1, x2, x3)
    if "UNIFAC" in model: return calc_gamma_unifac(x1, x2, x3)
    if "Van der Waals" in model: return 0.98, 0.97, 0.96
    if "Peng-Robinson" in model: return 0.95, 0.90, 0.92
    return 1.0, 1.0, 1.0

def calc_point(model, x1, x2, x3, T, p1_sat, p2_sat, p3_sat):
    g1, g2, g3 = get_activity(model, x1, x2, x3)
    P1 = x1 * g1 * p1_sat
    P2 = x2 * g2 * p2_sat
    P3 = x3 * g3 * p3_sat
    P_bub = P1 + P2 + P3
    y1 = P1 / P_bub if P_bub > 0 else 0
    y2 = P2 / P_bub if P_bub > 0 else 0
    y3 = P3 / P_bub if P_bub > 0 else 0
    return P_bub, y1, y2, y3, g1, g2, g3

def auto_select_model(T, P, comp1, comp2, comp3=None, mode="auto"):
    if mode == "compare": 
        return {"model": "Comparatif Multiple", "explanation": "Analyse simultanée via plusieurs modèles pour validation croisée."}
    
    if P > 1500: 
        return {"model": "Peng-Robinson", "explanation": "Haute pression (>15 bar) détectée. Peng-Robinson est l'équation d'état recommandée pour les gaz réels et fluides compressibles."}
    
    polars = ["Eau", "Éthanol", "Méthanol"]
    is_polar = comp1.name in polars or comp2.name in polars or (comp3 and comp3.name in polars)
    
    if is_polar:
        return {"model": "UNIQUAC / NRTL", "explanation": "Mélange polaire ou non-idéal détecté. Ces modèles d'activité sont précis pour les systèmes avec liaisons hydrogène ou fortes déviations à la loi de Raoult."}
    
    if P > 300: 
        return {"model": "Van der Waals", "explanation": "Pression modérée. Modèle prenant en compte le volume des molécules et les forces d'attraction intermoléculaires."}
    
    return {"model": "Raoult (Gaz Parfait)", "explanation": "Basse pression et mélange simple. La loi de Raoult est une excellente approximation pour les gaz parfaits et solutions idéales."}

def calculate_science_matrices(model, x1, T, P_sys, comp1, comp2, comp3=None, x2=None):
    if x2 is None:
        if comp3:
            x2 = (1.0 - x1) * 0.5
        else:
            x2 = 1.0 - x1
            
    x3 = 0.0
    if comp3:
        x3 = max(0.0, 1.0 - x1 - x2)
        total = x1 + x2 + x3
        if total > 0:
            x1, x2, x3 = x1/total, x2/total, x3/total
    else:
        total = x1 + x2
        if total > 0:
            x1, x2 = x1/total, x2/total
    
    # Propriétés de base
    p1_sat = calculate_vapor_pressure(comp1.antoine_A, comp1.antoine_B, comp1.antoine_C, T)
    p2_sat = calculate_vapor_pressure(comp2.antoine_A, comp2.antoine_B, comp2.antoine_C, T)
    p3_sat = calculate_vapor_pressure(comp3.antoine_A, comp3.antoine_B, comp3.antoine_C, T) if comp3 else 0.0
    
    P_bub, y1, y2, y3, g1, g2, g3 = calc_point(model, x1, x2, x3, T, p1_sat, p2_sat, p3_sat)
    
    # Constante d'équilibre et Z
    K1 = y1 / x1 if x1 > 0 else 0
    K2 = y2 / x2 if x2 > 0 else 0
    Z_factor = get_z_factor(P_sys, T, comp1.tc, comp1.pc)

    # -------- 1. Diagramme x-y (Equilibre VLE base)
    xy_curve = []
    for i in range(21):
        cx = i/20.0
        _, cy, _, _, _, _, _ = calc_point(model, cx, 1-cx, 0, T, p1_sat, p2_sat, 0)
        xy_curve.append({"x": cx, "y": cy})
        
    # -------- 2. Diagramme P-x-y (Isotherme)
    pxy_curve = []
    for i in range(21):
        cx = i/20.0
        pbub, cy, _, _, _, _, _ = calc_point(model, cx, 1-cx, 0, T, p1_sat, p2_sat, 0)
        pdew = 1.0 / ((cy / p1_sat) + ((1-cy) / p2_sat)) if p1_sat > 0 and p2_sat > 0 else 0 # Simplifié
        pxy_curve.append({"x": cx, "bubble": pbub, "dew": pdew})

    # -------- 3. Diagramme T-x-y (Isobarique) & Dew Point réel
    txy_curve = []
    # Calcul T ébullition corps purs
    t_boil_1 = comp1.antoine_B / (comp1.antoine_A - math.log10(P_sys/0.133322)) - comp1.antoine_C if P_sys > 0 else T
    t_boil_2 = comp2.antoine_B / (comp2.antoine_A - math.log10(P_sys/0.133322)) - comp2.antoine_C if P_sys > 0 else T
    
    t_min = min(t_boil_1, t_boil_2)
    t_max = max(t_boil_1, t_boil_2)
    
    for i in range(21):
        cx = i/20.0
        # Liner temp approximation for MVP Bubble/Dew points
        tbub = t_max - cx*(t_max - t_min)
        tdew = tbub + 10 * cx * (1-cx) # Simulated dew lens
        txy_curve.append({"x": cx, "bubble": tbub, "dew": tdew})

    # Point rosée actuel (y1)
    T_dew_actual = t_max - y1*(t_max - t_min) + 10 * y1 * (1-y1)
    P_dew_actual = 1.0 / ((y1 / p1_sat) + (y2 / p2_sat)) if p2_sat > 0 else P_sys

    # -------- 4 & 5. Profil de colonnes (Etapes)
    stages = 10
    profile_data = []
    curr_x1 = 0.05
    for s in range(stages):
        profile_data.append({"stage": s+1, "x1": curr_x1, "x2": 1-curr_x1})
        _, curr_y1, _, _, _, _, _ = calc_point(model, curr_x1, 1-curr_x1, 0, T, p1_sat, p2_sat, 0)
        curr_x1 = min(0.99, curr_y1 * 0.8 + 0.1)

    # -------- 6. Effet de la Température (+- 20°C)
    effect_t = []
    for dt in range(-20, 21, 5):
        test_T = T + dt
        test_p1 = calculate_vapor_pressure(comp1.antoine_A, comp1.antoine_B, comp1.antoine_C, test_T)
        test_p2 = calculate_vapor_pressure(comp2.antoine_A, comp2.antoine_B, comp2.antoine_C, test_T)
        _, test_y1, _, _, _, _, _ = calc_point(model, x1, x2, x3, test_T, test_p1, test_p2, 0)
        effect_t.append({"t": test_T, "enrichment": test_y1 - x1})

    # -------- 7. Effet de la Pression (+- 50%)
    effect_p = []
    for dp in [0.5, 0.7, 1.0, 1.3, 1.5, 1.8]:
        test_P = P_sys * dp
        ez = get_z_factor(test_P, T, comp1.tc, comp1.pc)
        effect_p.append({"p": test_P, "z": ez})

    return {
        "P_bubble": P_bub, "P_dew": P_dew_actual, "T_bubble": t_max - x1*(t_max-t_min), "T_dew": T_dew_actual,
        "y1": y1, "y2": y2, "y3": y3, "K1": K1, "K2": K2, "Z_factor": Z_factor, "gamma1": g1, "gamma2": g2,
        "alpha": (y1/x1)/(y2/x2) if x1 > 0 and x2 > 0 and y2 > 0 else 1.0,
        "diagrams": {
            "xy": xy_curve,
            "pxy": pxy_curve,
            "txy": txy_curve,
            "profile": profile_data,
            "effect_t": effect_t,
            "effect_p": effect_p
        }
    }

def calculate_mccabe_thiele(x_f, x_d, x_b, R, q, xy_curve, F_flow=100.0):
    if x_d != x_b:
        D_flow = F_flow * (x_f - x_b) / (x_d - x_b)
        W_flow = F_flow - D_flow
    else:
        D_flow = F_flow / 2.0
        W_flow = F_flow / 2.0
    if q == 1:
        x_int = x_f
        y_int = (R / (R + 1)) * x_int + x_d / (R + 1)
    else:
        m_q = q / (q - 1)
        b_q = -x_f / (q - 1)
        m_r = R / (R + 1)
        b_r = x_d / (R + 1)
        if (m_q - m_r) == 0:
            x_int = x_f
            y_int = x_f
        else:
            x_int = (b_r - b_q) / (m_q - m_r)
            y_int = m_r * x_int + b_r

    stages = []
    current_x = x_d
    current_y = x_d
    
    def get_x_eq(y_target):
        for i in range(len(xy_curve) - 1):
            p1 = xy_curve[i]
            p2 = xy_curve[i+1]
            if p1["y"] <= y_target <= p2["y"] or p2["y"] <= y_target <= p1["y"]:
                if p2["y"] == p1["y"]: return p1["x"]
                return p1["x"] + (y_target - p1["y"]) * (p2["x"] - p1["x"]) / (p2["y"] - p1["y"])
        return y_target

    def get_y_op(x):
        if x > x_int:
            return (R / (R + 1)) * x + x_d / (R + 1)
        else:
            return y_int - ((y_int - x_b) / (x_int - x_b)) * (x_int - x) if x_int != x_b else x

    stages.append({"x": current_x, "y": current_y})
    step_count = 0
    feed_stage = 0
    
    while current_x > x_b and step_count < 100:
        x_eq = get_x_eq(current_y)
        stages.append({"x": x_eq, "y": current_y})
        
        if x_eq < x_int and feed_stage == 0:
            feed_stage = step_count + 1
            
        current_x = x_eq
        if current_x <= x_b: break
        
        y_op = get_y_op(current_x)
        stages.append({"x": current_x, "y": y_op})
        current_y = y_op
        step_count += 1
        
    return {
        "stages": stages,
        "n_stages": step_count,
        "feed_stage": feed_stage,
        "lines": {
            "rectifying": [{"x": x_d, "y": x_d}, {"x": x_int, "y": y_int}],
            "stripping": [{"x": x_b, "y": x_b}, {"x": x_int, "y": y_int}],
            "q_line": [{"x": x_f, "y": x_f}, {"x": x_int, "y": y_int}]
        },
        "flows": {
            "F": F_flow,
            "D": D_flow,
            "W": W_flow
        }
    }

def calculate_pump(flow_rate_m3h, P_in_kpa, P_out_kpa, efficiency=0.75):
    delta_p = P_out_kpa - P_in_kpa
    if delta_p < 0:
        return {
            "work_kw": 0,
            "status": "Erreur: P_out < P_in",
            "success": False,
            "inputs": {"flow_rate_m3h": flow_rate_m3h, "P_in_kpa": P_in_kpa, "P_out_kpa": P_out_kpa, "efficiency": efficiency},
            "outputs": {"work_kw": 0, "delta_p": delta_p}
        }
    flow_rate_m3s = flow_rate_m3h / 3600.0
    work_w = (flow_rate_m3s * delta_p * 1000) / efficiency
    work_kw = round(work_w / 1000, 2)
    return {
        "work_kw": work_kw,
        "delta_p": delta_p,
        "success": True,
        "inputs": {
            "flow_rate_m3h": round(flow_rate_m3h, 2),
            "P_in_kpa": round(P_in_kpa, 2),
            "P_out_kpa": round(P_out_kpa, 2),
            "efficiency": round(efficiency * 100, 1)
        },
        "outputs": {
            "work_kw": work_kw,
            "delta_p": round(delta_p, 2),
            "success": True
        }
    }

def calculate_compressor(flow_rate_m3h, T_in_c, P_in_kpa, P_out_kpa, efficiency=0.75, gamma=1.4):
    if P_out_kpa < P_in_kpa:
        return {
            "work_kw": 0,
            "status": "Erreur: P_out < P_in",
            "success": False,
            "inputs": {"flow_rate_m3h": flow_rate_m3h, "T_in_c": T_in_c, "P_in_kpa": P_in_kpa, "P_out_kpa": P_out_kpa},
            "outputs": {"work_kw": 0, "t_out": T_in_c}
        }
    P1 = P_in_kpa * 1000
    P2 = P_out_kpa * 1000
    Q = flow_rate_m3h / 3600.0
    work_w = (gamma / (gamma - 1)) * P1 * Q * ((P2/P1)**((gamma - 1)/gamma) - 1) / efficiency
    T_out_isentropic = (T_in_c + 273.15) * ((P2/P1)**((gamma - 1)/gamma)) - 273.15
    work_kw = round(work_w / 1000, 2)
    t_out = round(T_out_isentropic, 1)
    return {
        "work_kw": work_kw,
        "t_out": t_out,
        "success": True,
        "inputs": {
            "flow_rate_m3h": round(flow_rate_m3h, 2),
            "T_in_c": round(T_in_c, 1),
            "P_in_kpa": round(P_in_kpa, 2),
            "P_out_kpa": round(P_out_kpa, 2),
            "efficiency": round(efficiency * 100, 1)
        },
        "outputs": {
            "work_kw": work_kw,
            "T_out_c": t_out,
            "success": True
        }
    }

def calculate_heat_exchanger(flow_rate_kgh, cp_kj_kg, T_in, T_out):
    duty_kw = (flow_rate_kgh / 3600.0) * cp_kj_kg * (T_out - T_in)
    duty_kw = round(duty_kw, 2)
    return {
        "duty_kw": duty_kw,
        "t_out": round(T_out, 1),
        "success": True,
        "inputs": {
            "flow_rate_kgh": round(flow_rate_kgh, 2),
            "cp_kj_kg": round(cp_kj_kg, 2),
            "T_in_c": round(T_in, 1),
            "T_out_c": round(T_out, 1)
        },
        "outputs": {
            "duty_kw": duty_kw,
            "delta_T_c": round(T_out - T_in, 1),
            "success": True
        }
    }

import math

def calculate_lle_stages(xf, xn, ys, S, F, K):
    """
    xf: fraction soluté dans l'alimentation
    xn: fraction soluté cible dans le raffinat
    ys: fraction soluté dans le solvant entrant
    S: débit solvant (V)
    F: débit charge (L)
    K: coefficient de partage (y/x)
    """
    if F == 0: return {"n_stages": 0, "error": "Débit d'alimentation (F) nul."}
    
    # 1. Méthode analytique de Kremser
    E = K * S / F  # Facteur d'extraction
    
    n_kremser = 0
    error = None
    if E == 1.0:
        n_kremser = (xf - xn) / (xn - ys/K)
    elif E <= 0:
        error = "Facteur d'extraction invalide (E <= 0)"
    else:
        try:
            term1 = (xf - ys/K) / (xn - ys/K)
            term2 = term1 * (1.0 - 1.0/E) + 1.0/E
            if term2 <= 0:
                error = "Cible inatteignable avec ces débits (pincement)"
            else:
                n_kremser = math.log(term2) / math.log(E)
        except Exception as e:
            error = str(e)

    # 2. Modélisation de la Binodale (Haute résolution, forme de dôme physiquement valide)
    raffinate_curve = []
    extract_curve = []
    binodal = []
    
    # Paramètre t de 0 (Base Extrait, riche en solvant) à 1 (Base Raffinat, riche en diluant)
    for i in range(1001):
        t = i / 1000.0
        A_raw = t * 0.9 + 0.05      # Diluant
        B_raw = (1.0 - t) * 0.9 + 0.05 # Solvant
        C_raw = 1.6 * t * (1.0 - t) # Soluté (Crée le dôme)
        S_sum = A_raw + B_raw + C_raw
        
        pt = {
            "solute": C_raw / S_sum,
            "solvent": B_raw / S_sum,
            "diluent": A_raw / S_sum
        }
        
        binodal.append(pt)
        
        # Le point de plissement est à t=0.5
        if t >= 0.5:
            raffinate_curve.append(pt) # t de 0.5 à 1.0 (Plissement vers Base Raffinat)
        if t <= 0.5:
            extract_curve.append(pt)   # t de 0 à 0.5 (Base Extrait vers Plissement)
            
    # On trie les courbes de la base vers le point de plissement pour faciliter la recherche
    raffinate_curve.reverse() # Maintenant: de t=1.0 (base) à t=0.5 (plissement)
    # L'extrait est déjà de t=0 (base) à t=0.5 (plissement)

    # Fonctions utilitaires pour le diagramme ternaire
    def get_pt(c, b): return {"solute": c, "solvent": b, "diluent": 1.0 - c - b}
    
    def dist_to_line(pt, line_p1, line_p2):
        # Distance d'un point pt à la ligne définie par p1 et p2 (dans le plan (solvant, soluté) = (b, c))
        num = abs((line_p2["solvent"] - line_p1["solvent"]) * (line_p1["solute"] - pt["solute"]) - 
                  (line_p1["solvent"] - pt["solvent"]) * (line_p2["solute"] - line_p1["solute"]))
        den = math.sqrt((line_p2["solvent"] - line_p1["solvent"])**2 + (line_p2["solute"] - line_p1["solute"])**2)
        return num / den if den != 0 else 9999

    def intersect_line_curve(p1, p2, curve):
        best_pt = curve[0]
        min_d = 9999
        for pt in curve:
            d = dist_to_line(pt, p1, p2)
            if d < min_d:
                min_d = d
                best_pt = pt
        return best_pt

    def get_equilibrium_raffinate(e_pt):
        target_c = e_pt["solute"] / K
        best_pt = raffinate_curve[0]
        min_diff = 9999
        for pt in raffinate_curve:
            diff = abs(pt["solute"] - target_c)
            if diff < min_diff:
                min_diff = diff
                best_pt = pt
        return best_pt

    # 3. Méthode de Hunter-Nash (Graphique Ternaire)
    F_pt = get_pt(xf, 0.0)
    S_pt = get_pt(ys, 1.0 - ys)
    
    # Point de mélange M
    M_c = (F * xf + S * ys) / (F + S)
    M_b = (F * 0.0 + S * (1.0 - ys)) / (F + S)
    M_pt = get_pt(M_c, M_b)
    
    # Point Raffinat cible Rn
    # On cherche le point sur la courbe de raffinat ayant solute = xn
    Rn_pt = raffinate_curve[0]
    for pt in raffinate_curve:
        if abs(pt["solute"] - xn) < abs(Rn_pt["solute"] - xn):
            Rn_pt = pt

    # Extrait E1 (Intersection de la ligne Rn-M avec la courbe d'extrait)
    E1_pt = intersect_line_curve(Rn_pt, M_pt, extract_curve)

    # Calcul du Pôle de différence P (Intersection F-E1 et S-Rn)
    try:
        m1 = (E1_pt["solute"] - F_pt["solute"]) / (E1_pt["solvent"] - F_pt["solvent"]) if E1_pt["solvent"] != F_pt["solvent"] else 9999
        m2 = (Rn_pt["solute"] - S_pt["solute"]) / (Rn_pt["solvent"] - S_pt["solvent"]) if Rn_pt["solvent"] != S_pt["solvent"] else 9999
        
        if abs(m1 - m2) < 1e-5:
            raise Exception("Lignes parallèles (Pôle à l'infini)")
            
        b_P = (m1 * F_pt["solvent"] - m2 * S_pt["solvent"] + S_pt["solute"] - F_pt["solute"]) / (m1 - m2)
        c_P = m1 * (b_P - F_pt["solvent"]) + F_pt["solute"]
        P_pt = get_pt(c_P, b_P)
    except:
        P_pt = get_pt(0, -1) # Fallback

    # Construction des étages
    hn_stages = []
    operating_lines = []
    tie_lines_actual = []
    
    curr_E = E1_pt
    steps = 0
    max_steps = 20
    
    while steps < max_steps:
        # 1. Equilibre: E_i -> R_i
        curr_R = get_equilibrium_raffinate(curr_E)
        tie_lines_actual.append([curr_E, curr_R])
        
        # Sauvegarde des propriétés de l'étage
        hn_stages.append({
            "stage": steps + 1,
            "extract": curr_E,
            "raffinate": curr_R
        })
        
        # 2. Vérification d'arrêt
        if curr_R["solute"] <= xn:
            break
            
        # 3. Ligne opératoire: P_pt-curr_R -> intersecte l'extrait pour donner E_{i+1}
        next_E = intersect_line_curve(P_pt, curr_R, extract_curve)
        operating_lines.append([P_pt, curr_R, next_E]) # Pour le tracé
        
        curr_E = next_E
        steps += 1

    M_mass = F + S
    if E1_pt["solute"] != Rn_pt["solute"]:
        E_mass = M_mass * (M_pt["solute"] - Rn_pt["solute"]) / (E1_pt["solute"] - Rn_pt["solute"])
    else:
        E_mass = M_mass / 2.0
    R_mass = M_mass - E_mass

    return {
        "n_kremser": round(n_kremser, 1) if not error else 0,
        "n_hn": steps,
        "n_stages": steps,
        "stage_data": hn_stages,
        "error": error,
        "success": not error,
        "E": round(E, 2),
        "K": round(K, 2),
        "binodal": binodal,
        "tie_lines": tie_lines_actual,
        "operating_lines": operating_lines,
        "points": {
            "feed": F_pt,
            "solvent": S_pt,
            "raffinate": Rn_pt,
            "extract": E1_pt,
            "mixture": M_pt,
            "pole": P_pt
        },
        "flows": {
            "L": F,
            "V": S,
            "E": E_mass,
            "R": R_mass
        },
        "inputs": {
            "xF": round(xf * 100, 2),
            "xN": round(xn * 100, 2),
            "yS": round(ys * 100, 2),
            "F_kmol_h": round(F, 2),
            "S_kmol_h": round(S, 2),
            "K": round(K, 3),
        },
        "outputs": {
            "n_stages": steps,
            "n_kremser": round(n_kremser, 1) if not error else 0,
            "E_kmol_h": round(E_mass, 2),
            "R_kmol_h": round(R_mass, 2),
            "success": not error,
        }
    }


def calculate_absorption(y_in, y_out, x_in, G, L, K, hetp=0.5):
    """
    Calcule les étages théoriques pour une colonne d'absorption de gaz
    utilisant l'équation de Kremser.
    Hypothèse : solutions diluées, G et L constants.
    """
    # Facteur d'absorption
    A = L / (K * G)
    
    # Débit liquide minimum L_min
    # A un nombre infini d'étages, le liquide sortant (x_out) est en équilibre avec le gaz entrant (y_in)
    x_out_max = y_in / K
    if x_out_max > x_in:
        L_min = G * (y_in - y_out) / (x_out_max - x_in)
    else:
        L_min = 0 # Pas de transfert possible dans ce sens
        
    # Calcul x_out réel (Bilan global)
    # G * y_in + L * x_in = G * y_out + L * x_out
    x_out = x_in + (G / L) * (y_in - y_out)
    
    # Calcul du nombre d'étages théoriques (Kremser)
    if A == 1.0:
        n_stages = (y_in - y_out) / (y_out - K * x_in)
    else:
        num = ((y_in - K * x_in) / (y_out - K * x_in)) * (1 - 1/A) + 1/A
        if num <= 0:
            n_stages = 999 # Impossible ou infini
        else:
            n_stages = math.log(num) / math.log(A)
            
    # Génération des points pour le diagramme (Droite op et équilibre)
    # y = K * x
    eq_line = [
        {"x": 0, "y": 0},
        {"x": max(x_out, x_in, x_out_max) * 1.2, "y": K * max(x_out, x_in, x_out_max) * 1.2}
    ]
    
    # Droite opératoire: passe par (x_in, y_out) en haut, et (x_out, y_in) en bas
    op_line = [
        {"x": x_in, "y": y_out},
        {"x": x_out, "y": y_in}
    ]
    
    # Tracé des étages en escalier (de haut en bas)
    # On commence à (x_in, y_out)
    stages_points = [{"x": x_in, "y": y_out}]
    current_x = x_in
    current_y = y_out
    stage_count = 0
    
    # Pour le tracé on s'arrête quand on dépasse y_in
    while current_y < y_in and stage_count < 50:
        stage_count += 1
        # 1. Equilibre: aller horizontalement vers la courbe d'équilibre
        new_x = current_y / K
        stages_points.append({"x": new_x, "y": current_y})
        # 2. Bilan: aller verticalement vers la droite opératoire
        # y = (L/G)*x + y_out - (L/G)*x_in
        new_y = (L/G) * new_x + y_out - (L/G) * x_in
        
        # Limiter pour la dernière étape si ça dépasse y_in
        if new_y > y_in:
            new_y = y_in
            stages_points.append({"x": new_x, "y": new_y})
            break
            
        stages_points.append({"x": new_x, "y": new_y})
        
        current_x = new_x
        current_y = new_y
        
    # Hauteur de la colonne à garnissage
    Z = n_stages * hetp if n_stages != 999 else 999
        
    return {
        "A": A,
        "L_min": L_min,
        "x_out": x_out,
        "n_stages": n_stages,
        "hetp": hetp,
        "Z": Z,
        "diagram": {
            "eq_line": eq_line,
            "op_line": op_line,
            "stages": stages_points
        }
    }
