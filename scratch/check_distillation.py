"""Quick sanity check for distillation results."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import Component
import distillation_engine as de
import validation_engine as ve


def test_case(label, c1n, c2n, F, xf, xd, xb, R, q):
    with app.app_context():
        comps = {c.name: c for c in Component.query.all()}
        c1 = comps.get(c1n) or list(comps.values())[0]
        c2 = comps.get(c2n) or list(comps.values())[1]
        r = de.calculate_distillation_advanced(
            F, xf, xd, xb, R, q, 101.325, c1, c2, "NRTL", 0.75
        )
        if not r.get("success"):
            print(label, "FAIL", r.get("error"))
            return
        D, B = r["flows"]["D"], r["flows"]["B"]
        mb = abs(F * xf - (D * xd + B * xb))
        v = ve.validate_distillation_complete(
            F, xf, xd, xb, D, B, R, r["R_min"], q, 101.325,
            r["N_min"], r["N_theo"], r["N_reel"],
            r["energy"]["Q_condenser"], r["energy"]["Q_reboiler"],
            r["flows"]["V"], r.get("xy_curve"),
        )
        print(f"--- {label} ({c1.name} / {c2.name}) ---")
        print(
            f"  N_min={r['N_min']} R_min={r['R_min']:.2f} "
            f"N_theo={r['N_theo']} N_steps={r['N_steps']} N_reel={r['N_reel']}"
        )
        print(f"  bilan composant err={mb:.4f} valid={v.is_valid} errors={len(v.errors)}")
        for e in v.errors[:4]:
            print("   ", e.get("code"), str(e.get("message", ""))[:100])


if __name__ == "__main__":
    test_case("ethanol-eau", "Éthanol", "Eau", 100, 0.4, 0.85, 0.05, 2.0, 1.0)
    test_case("benzene-toluene", "Benzène", "Toluène", 100, 0.5, 0.95, 0.05, 3.0, 1.0)
    test_case("hexane-heptane", "n-Hexane", "n-Heptane", 100, 0.5, 0.90, 0.10, 2.5, 1.0)
