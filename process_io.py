"""
Entrées / sorties par opération unitaire — séparation stricte entre procédés.
"""

from __future__ import annotations


def _f(form, key, default, cast=float):
    v = form.get(key, default)
    try:
        return cast(v)
    except (TypeError, ValueError):
        return default


def needs_global_vle(process_types):
    return bool(set(process_types) & {"distillation", "flash"})


def needs_global_thermo(process_types):
    return needs_global_vle(process_types) or "compare" in str(process_types)


def parse_distillation_inputs(form, comp1, comp2, T, P_sys, x_feed, feed_q, thermo_model):
    return {
        "process": "distillation",
        "xD": _f(form, "dist_x_d", 0.95),
        "xB": _f(form, "dist_x_b", 0.05),
        "F_kmol_h": _f(form, "dist_flow_f", 100.0),
        "R": _f(form, "dist_reflux", 1.5),
        "q": feed_q,
        "tray_efficiency": _f(form, "dist_tray_efficiency", 0.75),
        "thermo_model": thermo_model,
        "x_feed": x_feed,
        "T_C": T,
        "P_kPa": P_sys,
        "comp_light": comp1.name if comp1 else "",
        "comp_heavy": comp2.name if comp2 else "",
    }


def distillation_outputs(dist_result):
    if not dist_result:
        return {}
    return {
        "n_stages": dist_result.get("n_stages"),
        "N_min": dist_result.get("N_min"),
        "R_min": dist_result.get("R_min"),
        "feed_stage": dist_result.get("feed_stage"),
        "success": dist_result.get("success", True),
        "flows": dist_result.get("flows"),
        "energy": dist_result.get("energy"),
        "error": dist_result.get("error"),
    }


def parse_flash_inputs(form, T, P_sys, x_feed, comp1, comp2):
    dp = _f(form, "flash_dp", 0.0)
    return {
        "process": "flash",
        "psi": _f(form, "flash_psi", 0.5),
        "dp_kPa": dp,
        "T_C": T,
        "P_in_kPa": P_sys,
        "P_flash_kPa": P_sys - dp,
        "x_feed": x_feed,
        "comp1": comp1.name if comp1 else "",
        "comp2": comp2.name if comp2 else "",
    }


def run_flash(inputs):
    psi = inputs["psi"]
    return {
        "psi": psi,
        "dp": inputs["dp_kPa"],
        "t_flash": inputs["T_C"],
        "p_flash": inputs["P_flash_kPa"],
        "flow_v_pct": round(psi * 100, 1),
        "flow_l_pct": round((1 - psi) * 100, 1),
    }


def parse_pump_inputs(form, P_sys, comp1):
    return {
        "process": "pump",
        "flow_m3_h": _f(form, "pump_flow_rate", 100.0),
        "P_in_kPa": _f(form, "pump_p_in", P_sys),
        "P_out_kPa": _f(form, "pump_p_out", P_sys + 100),
        "efficiency": _f(form, "pump_efficiency", 0.75),
        "fluid": comp1.name if comp1 else "",
    }


def pump_outputs(raw):
    return {
        "work_kW": raw.get("work_kw"),
        "delta_P_kPa": raw.get("delta_p"),
        "status": raw.get("status"),
    }


def parse_compressor_inputs(form, P_sys, comp1, T_default):
    return {
        "process": "compressor",
        "flow_m3_h": _f(form, "comp_flow_rate", 100.0),
        "T_in_C": _f(form, "comp_T_in", T_default),
        "P_in_kPa": _f(form, "comp_p_in", P_sys),
        "P_out_kPa": _f(form, "comp_p_out", P_sys + 500),
        "efficiency": _f(form, "comp_efficiency", 0.75),
        "fluid": comp1.name if comp1 else "",
    }


def compressor_outputs(raw):
    return {
        "work_kW": raw.get("work_kw"),
        "T_out_C": raw.get("t_out"),
        "status": raw.get("status"),
    }


def parse_hex_inputs(form):
    return {
        "process": "heat_exchanger",
        "T_in_hot_C": _f(form, "hex_t_in_hot", 150.0),
        "T_out_hot_C": _f(form, "hex_t_out_hot", 80.0),
        "T_in_cold_C": _f(form, "hex_t_in_cold", 20.0),
        "T_out_cold_C": _f(form, "hex_t_out_cold", 90.0),
        "flow_hot_kg_h": _f(form, "hex_flow_rate", 1000.0),
        "Cp_kJ_kgK": _f(form, "hex_cp", 2.0),
        "mode": form.get("hex_mode", "counter_current"),
    }


def run_hex(inputs):
    import thermo_engine
    fh = inputs["flow_hot_kg_h"]
    cp = inputs["Cp_kJ_kgK"]
    t_in = inputs["T_in_hot_C"]
    t_out = inputs["T_out_hot_C"]
    duty_hot = thermo_engine.calculate_heat_exchanger(fh, cp, t_in, t_out)
    dt_hot = t_in - t_out
    dt_cold = inputs["T_out_cold_C"] - inputs["T_in_cold_C"]
    duty_cold = (fh / 3600.0) * cp * dt_cold if dt_cold else 0
    return {
        "duty_kw": duty_hot.get("duty_kw", 0),
        "duty_cold_kw": round(abs(duty_cold), 2),
        "delta_T_hot_C": round(dt_hot, 2),
        "delta_T_cold_C": round(dt_cold, 2),
        "T_out_hot_C": t_out,
        "T_out_cold_C": inputs["T_out_cold_C"],
        "balance_ok": abs(abs(duty_hot.get("duty_kw", 0)) - abs(duty_cold)) < 50,
    }


def hex_outputs(raw):
    return {
        "duty_kW": raw.get("duty_kw"),
        "duty_cold_kW": raw.get("duty_cold_kw"),
        "delta_T_hot_C": raw.get("delta_T_hot_C"),
        "delta_T_cold_C": raw.get("delta_T_cold_C"),
        "balance_ok": raw.get("balance_ok"),
    }


def attach_process_result(raw: dict, inputs: dict, outputs: dict) -> dict:
    """Enveloppe standard : inputs + outputs + champs moteur."""
    return {
        **raw,
        "process": inputs.get("process", raw.get("process")),
        "inputs": inputs,
        "outputs": outputs,
    }
