# diagnostic_engine.py

def run_diagnostics(process_type, inputs, results):
    """
    Analyse les paramètres d'entrée et les résultats pour générer des diagnostics intelligents.
    Retourne une liste d'alertes : { "level": "CRITICAL"|"WARNING"|"SAFE", "message": "...", "solutions": [...] }
    """
    diagnostics = []

    if process_type == 'distillation':
        diagnostics.extend(_check_distillation(inputs, results))
    elif process_type == 'extraction':
        diagnostics.extend(_check_extraction(inputs, results))
    elif process_type == 'absorption':
        diagnostics.extend(_check_absorption(inputs, results))
    elif process_type == 'pump':
        diagnostics.extend(_check_pump(inputs, results))
    elif process_type == 'heat_exchanger':
        diagnostics.extend(_check_heat_exchanger(inputs, results))

    # Si aucune alerte majeure n'est trouvée, on ajoute un message SAFE général
    if not any(d['level'] in ['CRITICAL', 'WARNING'] for d in diagnostics):
        diagnostics.insert(0, {
            "level": "SAFE",
            "message": "Configuration optimale.",
            "solutions": ["Les paramètres opérationnels sont dans les normes industrielles."]
        })

    return diagnostics


def _check_distillation(inputs, results):
    diags = []
    reflux = float(inputs.get('reflux_ratio', 0))
    stages = int(inputs.get('stages', 0))
    
    # Check Reflux
    if reflux < 0.5:
        diags.append({
            "level": "WARNING",
            "message": "Taux de reflux extrêmement faible.",
            "solutions": [
                "Risque de pincement (purity inatteignable).",
                "Augmentez le taux de reflux pour faciliter la séparation."
            ]
        })
    elif reflux > 5:
        diags.append({
            "level": "WARNING",
            "message": "Taux de reflux très élevé.",
            "solutions": [
                "Consommation énergétique excessive au bouilleur.",
                "Envisagez d'augmenter le nombre de plateaux au lieu du reflux."
            ]
        })

    # McCabe-Thiele results
    if results and 'op_results' in results and 'mccabe' in results['op_results']:
        n_calc = results['op_results']['mccabe'].get('n_stages', 0)
        if stages > 0 and n_calc > stages:
            diags.append({
                "level": "CRITICAL",
                "message": f"Nombre de plateaux insuffisant (Requis: {n_calc}, Fourni: {stages}).",
                "solutions": [
                    "La pureté cible est mathématiquement impossible avec cette colonne.",
                    "Ajoutez des plateaux ou augmentez fortement le reflux."
                ]
            })

    return diags


def _check_extraction(inputs, results):
    diags = []
    op_res = results.get('op_results', {}).get('extraction', {})
    E = op_res.get('E', 1)
    K = op_res.get('K', 1)
    validation = op_res.get('validation', {})

    if not validation.get('is_valid', True):
        for err in validation.get('errors', []):
            diags.append({
                "level": "CRITICAL",
                "message": err.get('message', 'Validation extraction échouée'),
                "solutions": ["Corriger les compositions ou débits.", "Vérifier K et le ratio S/F."]
            })

    if E < 1.0:
        diags.append({
            "level": "CRITICAL",
            "message": "Facteur d'extraction (E = K·S/F < 1) : solvant insuffisant.",
            "solutions": [
                "Augmentez le débit de solvant S ou réduisez F.",
                "Choisissez un solvant avec K plus élevé.",
            ]
        })
    elif E > 10:
        diags.append({
            "level": "WARNING",
            "message": "Facteur d'extraction (E) excessif — dilution de l'extrait.",
            "solutions": [
                "Réduisez S/F pour limiter le coût de régénération du solvant.",
            ]
        })

    if K < 0.5:
        diags.append({
            "level": "WARNING",
            "message": f"Coefficient de partage K={K:.2f} trop faible.",
            "solutions": ["Séparation L-L difficile.", "Changer de solvant ou ajuster T."]
        })

    n_st = op_res.get('n_stages', op_res.get('n_hn', 0))
    n_kr = op_res.get('n_kremser', 0)
    if n_st > 0 and n_kr > 0 and abs(n_st - n_kr) / max(n_kr, 0.1) > 0.4:
        diags.append({
            "level": "WARNING",
            "message": f"Écart McCabe-Thiele ({n_st}) vs Kremser ({n_kr}).",
            "solutions": ["Vérifier la courbe d'équilibre et le mode de procédé."]
        })

    hydro = op_res.get('hydrodynamics', {})
    if hydro.get('flooding'):
        diags.append({
            "level": "CRITICAL",
            "message": "Risque de flooding colonne (S/F excessif).",
            "solutions": ["Réduire S/F.", "Vérifier vitesse et aération de la colonne."]
        })
    if hydro.get('emulsion_risk'):
        diags.append({
            "level": "WARNING",
            "message": "Risque d'émulsion / mauvaise séparation.",
            "solutions": ["Ajuster interfaces.", "Contrôler tension superficielle et agitation."]
        })

    yld = op_res.get('yield_pct', 0)
    if yld < 30 and op_res.get('flows', {}).get('L', 0) > 0:
        diags.append({
            "level": "WARNING",
            "message": f"Rendement d'extraction faible ({yld:.0f}%).",
            "solutions": ["Augmenter S/F.", "Améliorer K.", "Ajouter des étages."]
        })

    if n_st > 15 or op_res.get('n_hn', 0) > 15:
        diags.append({
            "level": "WARNING",
            "message": "Nombre d'étages théoriques très élevé.",
            "solutions": [
                "Colonne haute et coûteuse.",
                "Envisager solvant plus sélectif ou extracteur centrifuge.",
            ]
        })

    if op_res.get('error'):
        diags.append({
            "level": "CRITICAL",
            "message": op_res['error'],
            "solutions": ["Revoir xF, xR cible, K et débits F/S."]
        })

    return diags


def _check_pump(inputs, results):
    diags = []
    eff = float(inputs.get('efficiency', 0.75))
    delta_p = float(inputs.get('delta_p', 0))
    npsha = float(inputs.get('npsha', 0))
    npshr = float(inputs.get('npshr', 0))

    if npsha > 0 and npshr > 0:
        if npsha < npshr:
            diags.append({
                "level": "CRITICAL",
                "message": "Risque majeur de Cavitation (NPSHa < NPSHr).",
                "solutions": [
                    "Augmenter la pression à l'aspiration (élever le bac).",
                    "Réduire la température du fluide (pour baisser la pression de vapeur saturante).",
                    "Réduire les pertes de charge à l'aspiration (tuyau plus large, moins de coudes)."
                ]
            })
        elif (npsha - npshr) < 1.0:
            diags.append({
                "level": "WARNING",
                "message": "Marge NPSH très faible.",
                "solutions": ["Risque de cavitation en cas de fluctuation de débit."]
            })

    if eff < 0.5:
        diags.append({
            "level": "WARNING",
            "message": "Rendement de pompe trop faible.",
            "solutions": [
                "Pompe sous-dimensionnée ou sur-dimensionnée par rapport au point de fonctionnement.",
                "Gaspillage énergétique important."
            ]
        })
    elif eff > 0.95:
         diags.append({
            "level": "CRITICAL",
            "message": "Rendement irréaliste pour une pompe centrifuge.",
            "solutions": ["Vérifiez vos paramètres d'entrée."]
        })

    if delta_p > 30:
        diags.append({
            "level": "WARNING",
            "message": "Pression de refoulement très élevée pour un seul étage.",
            "solutions": [
                "Vibration, usure prématurée.",
                "Utilisez une pompe multi-étagée ou une pompe volumétrique."
            ]
        })

    return diags


def _check_heat_exchanger(inputs, results):
    diags = []
    t_in_h = float(inputs.get('t_in_hot', 0))
    t_out_h = float(inputs.get('t_out_hot', 0))
    t_in_c = float(inputs.get('t_in_cold', 0))
    t_out_c = float(inputs.get('t_out_cold', 0))
    flow_type = inputs.get('flow_type', 'counter') # 'counter' or 'co'

    # Validité de base
    if t_out_h > t_in_h:
        diags.append({
            "level": "CRITICAL",
            "message": "Violation thermodynamique : Le fluide chaud se réchauffe.",
            "solutions": ["Vérifiez les températures saisies."]
        })
    if t_out_c < t_in_c:
        diags.append({
            "level": "CRITICAL",
            "message": "Violation thermodynamique : Le fluide froid se refroidit.",
            "solutions": ["Vérifiez les températures saisies."]
        })

    # Pincement thermique
    if flow_type == 'counter':
        dt1 = t_in_h - t_out_c
        dt2 = t_out_h - t_in_c
    else: # co-current
        dt1 = t_in_h - t_in_c
        dt2 = t_out_h - t_out_c

    if dt1 < 0 or dt2 < 0:
        diags.append({
            "level": "CRITICAL",
            "message": "Croisement de température impossible (Pincement thermique négatif).",
            "solutions": [
                "2ème Principe de la thermodynamique violé.",
                "La chaleur ne peut pas passer du fluide froid vers le fluide chaud."
            ]
        })
    elif dt1 < 5 or dt2 < 5:
        diags.append({
            "level": "WARNING",
            "message": "Pincement thermique très faible (Approche < 5°C).",
            "solutions": [
                "Nécessitera une surface d'échange (et un coût) infiniment grande.",
                "Modifiez les débits ou les températures cibles."
            ]
        })

    return diags


def _check_absorption(inputs, results):
    diags = []

    y_in = float(inputs.get('abs_y_in', 0))
    y_out = float(inputs.get('abs_y_out', 0))
    x_in = float(inputs.get('abs_x_in', 0))
    L = float(inputs.get('abs_flow_l', 1))
    G = float(inputs.get('abs_flow_g', 1))

    op_res = results.get('op_results', {}).get('absorption', {})
    A = op_res.get('A', 1)
    L_min = op_res.get('L_min', 0)
    m = op_res.get('m')
    if m is None or m < 0.1:
        m = float(inputs.get('abs_m', 0) or 0)
    if m < 0.1:
        m = 1.5
    hydro = op_res.get('hydrodynamics', {})
    n_st = op_res.get('n_stages', 0)

    if y_out <= m * x_in:
        diags.append({
            "level": "CRITICAL",
            "message": "Pureté cible thermodynamiquement impossible (y_out ≤ y* = m·x_in).",
            "solutions": [
                f"Limite d'équilibre : y* = {m * x_in:.5f}. Purifier le solvant ou augmenter m (température).",
                "Relâcher la contrainte sur y_out.",
            ],
        })

    if L_min < 99999 and L < L_min and L_min > 0:
        diags.append({
            "level": "CRITICAL",
            "message": "Débit liquide inférieur au minimum théorique L_min.",
            "solutions": [
                f"L_min requis ≈ {L_min:.1f} mol/h (séparation à étages infinis).",
                "Augmenter L ou réduire l'exigence sur y_out.",
            ],
        })

    if n_st >= 900 or n_st == 999:
        diags.append({
            "level": "CRITICAL",
            "message": "Séparation impossible ou divergence numérique (N étages → ∞).",
            "solutions": [
                "Augmenter L/G, améliorer le solvant (m plus favorable), ou revoir y_out.",
            ],
        })

    if hydro.get("flooding"):
        diags.append({
            "level": "CRITICAL",
            "message": "Risque de FLOODING — vitesse gaz proche du colmatage.",
            "solutions": [
                f"v_g = {hydro.get('v_gas_m_s', '?')} m/s — réduire G ou augmenter le diamètre.",
                "Vérifier le type de garnissage / plateaux et le débit liquide.",
            ],
        })

    if hydro.get("weeping"):
        diags.append({
            "level": "WARNING",
            "message": "Weeping probable sur plateaux (vitesse gaz trop faible).",
            "solutions": ["Augmenter le débit gaz ou revoir le design des plateaux."],
        })

    if hydro.get("insufficient_liquid"):
        diags.append({
            "level": "WARNING",
            "message": "Débit liquide insuffisant (L/G faible) pour le lavage du gaz.",
            "solutions": ["Augmenter L ou choisir un absorbant plus sélectif."],
        })

    if A < 1.0:
        diags.append({
            "level": "CRITICAL",
            "message": "Facteur d'absorption A < 1 — pincement / séparation limitée.",
            "solutions": [
                "Augmenter L ou diminuer m (meilleure solubilité du soluté).",
            ],
        })
    elif A < 1.25:
        diags.append({
            "level": "WARNING",
            "message": "Facteur A sous-optimal (< 1.25) — colonne très haute.",
            "solutions": ["Augmenter légèrement L pour viser A ≈ 1.4–1.6."],
        })
    elif A > 2.0:
        diags.append({
            "level": "WARNING",
            "message": "Facteur A très élevé (> 2) — surconsommation de solvant.",
            "solutions": ["Réduire L pour optimiser coût pompage / régénération."],
        })

    n_mt = op_res.get("n_mt", 0)
    n_kr = op_res.get("n_kremser", 0)
    if n_mt > 0 and n_kr > 0 and n_kr < 900:
        rel = abs(n_mt - n_kr) / max(n_kr, 0.1)
        if rel > 0.35:
            diags.append({
                "level": "WARNING",
                "message": f"Incohérence McCabe-Thiele ({n_mt}) vs Kremser ({n_kr:.1f}).",
                "solutions": ["Vérifier m, bilans et hypothèses diluées."],
            })

    return diags
