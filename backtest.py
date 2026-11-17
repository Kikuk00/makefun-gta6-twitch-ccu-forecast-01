"""Leave-one-out backtest for the GTA VI Twitch CCU forecaster (main.py).

For every comparable launch in the practice kit, pretend only its hour-1
print is known, forecast hours 2-24 with main.forecast_case() using the OTHER
comparables, and score the pinball loss on the log scale against that launch's
actual hours 2-24.  The house persistence baseline is scored the same way on
the same launches.  Also reports 90% coverage and typical miss.

This is the honest local check available: the practice cases' own answers are
not shipped in the kit (the server grades them), so the comparables are the
ground truth.  Run:  python3 backtest.py
"""
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main as entry

KIT = Path.home() / "workspace/makefun/kits/gta6-twitch-ccu-forecast-01-kit" \
    / "gta6-twitch-ccu-forecast-01-kit"
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]


def pinball(y, qs):
    ly = math.log(max(1.0, float(y)))
    total = 0.0
    for tau, q in zip(LEVELS, qs):
        d = ly - math.log(max(1e-9, float(q)))
        total += 2.0 * max(tau * d, (tau - 1.0) * d)
    return total / len(LEVELS)


def baseline_forecast(p1):
    out = {}
    for h in range(2, 25):
        out[h] = [round(p1 * math.exp(z * 0.15 * math.sqrt(h - 1)), 2) for z in Z]
    return out


def day_curve(comp):
    """Actual release-day hourly viewers {hour: viewers} for one comparable."""
    ds = datetime.fromisoformat(comp["day_start"].replace("Z", "+00:00"))
    curve = {}
    for row in comp.get("hourly") or []:
        viewers = row.get("viewers")
        if not viewers:
            continue
        when = datetime.fromisoformat(row["from"].replace("Z", "+00:00"))
        hour = int((when - ds).total_seconds() // 3600) + 1
        if 1 <= hour <= 24:
            curve[hour] = float(viewers)
    return curve


def run():
    practice = json.loads((KIT / "input" / "p00.in").read_text())
    comps = [c for c in practice["comparables"]
             if "Not a launch" not in str(c.get("unlock") or "")]
    curves = {c["name"]: day_curve(c) for c in comps}

    rows = []
    for target in comps:
        curve = curves[target["name"]]
        if 1 not in curve:
            continue
        p1 = curve[1]
        case = {
            "id": "loo",
            "levels": LEVELS,
            "known": [{"hour": 1, "viewers": p1}],
            "forecast": [{"hour": h} for h in range(2, 25)],
            "history_hourly": [],
            "comparables": [c for c in comps if c["name"] != target["name"]],
        }
        mine = {r["hour"]: r["q"] for r in entry.forecast_case(case)["hours"]}
        base = baseline_forecast(p1)
        scored = [h for h in range(2, 25) if h in curve]
        lm = sum(pinball(curve[h], mine[h]) for h in scored) / len(scored)
        lb = sum(pinball(curve[h], base[h]) for h in scored) / len(scored)
        covered = sum(1 for h in scored
                      if mine[h][0] <= curve[h] <= mine[h][-1]) / len(scored)
        miss = statistics.mean(abs(math.log(curve[h]) - math.log(mine[h][2]))
                               for h in scored)
        rows.append({"name": target["name"], "p1": p1, "mine": lm,
                     "base": lb, "coverage": covered, "miss": miss,
                     "n": len(scored)})

    def report(label, subset):
        sel = [r for r in rows if subset(r)]
        if not sel:
            return
        print(f"{label:28s} n={len(sel):2d}  mine={statistics.mean(r['mine'] for r in sel):.4f}"
              f"  baseline={statistics.mean(r['base'] for r in sel):.4f}"
              f"  coverage90={statistics.mean(r['coverage'] for r in sel):.3f}"
              f"  typical_miss={100 * (math.exp(statistics.mean(r['miss'] for r in sel)) - 1):.1f}%")

    report("ALL launches", lambda r: True)
    report("hour-1 > 20,000", lambda r: r["p1"] > 20000)
    report("hour-1 > 100,000", lambda r: r["p1"] > 100000)
    report("hour-1 < 5,000 (pre-unlock)", lambda r: r["p1"] < 5000)
    print()
    print("Per-launch (mine vs baseline):")
    for r in sorted(rows, key=lambda r: r["mine"] - r["base"]):
        print(f"  {r['name'][:40]:40s} p1={r['p1']:8.0f} mine={r['mine']:.3f} base={r['base']:.3f}")
    return rows


if __name__ == "__main__":
    run()
