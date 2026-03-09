#!/usr/bin/env python3
"""
Compute peer groups, benchmarks, and narrative flags for each commune.
Produces insights.json indexed by INSEE code.

Inputs: maires.json, surveillance.json, prospection.json, delinquance.json, enrichment.json
Output: insights.json
"""
import heapq
import json
import math
import os
import sys

# ---------------------------------------------------------------------------
# Thresholds for narrative flags
# ---------------------------------------------------------------------------
PCT_CRIME_ABOVE = 75       # percentile above which crime is flagged
PCT_PEERS_PM_MAJORITY = 50 # % of peers with PM to flag "no PM but peers have"
PCT_PEERS_VV_SIGNIFICANT = 30  # % of peers with VV to flag
PCT_ACCIDENT_ABOVE = 50    # percentile above which accidents are flagged
PCT_POVERTY_HIGH = 60      # percentile above which poverty is flagged
MIN_PEERS_FOR_BENCH = 3    # minimum peer values to compute a benchmark

# Peer matching weights (sum to 0.9; FAMILY_BONUS calibrated accordingly)
W_LOG_POP = 0.4
W_REV = 0.25
W_PAUV = 0.25
FAMILY_BONUS = -0.3
N_PEERS = 20


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_bench(my_val, peer_vals, round_digits=1):
    """Compute benchmark stats: {val, med, pct} or None if insufficient data."""
    vals = sorted(v for v in peer_vals if v is not None)
    if my_val is None or len(vals) < MIN_PEERS_FOR_BENCH:
        return None
    med = vals[len(vals) // 2]
    pct = sum(1 for v in vals if v < my_val) / len(vals) * 100
    return {"val": round(my_val, round_digits), "med": round(med, round_digits), "pct": round(pct)}


def mean_std(vals):
    """Return (mean, std) of vals; std floored at 0.001 to avoid division by zero."""
    n = len(vals)
    if n == 0:
        return 0, 1
    m = sum(vals) / n
    variance = sum((x - m) ** 2 for x in vals) / n
    return m, max(math.sqrt(variance), 0.001)


def main():
    base = os.path.dirname(__file__) or "."
    print("Loading data files...", file=sys.stderr)
    maires = load_json(os.path.join(base, "maires.json"))
    surv = load_json(os.path.join(base, "surveillance.json"))
    prosp = load_json(os.path.join(base, "prospection.json"))
    delinq = load_json(os.path.join(base, "delinquance.json"))
    enrich = load_json(os.path.join(base, "enrichment.json"))

    all_codes = set(maires) | set(surv) | set(prosp) | set(delinq) | set(enrich)
    print(f"  {len(all_codes)} total commune codes", file=sys.stderr)

    # Step 1: Build feature vectors for peer matching
    vectors = {}
    pops = {}
    for code in all_codes:
        pop = 0
        if code in prosp and prosp[code].get("pop"):
            pop = prosp[code]["pop"]
        elif code in surv and surv[code].get("pop"):
            pop = surv[code]["pop"]
        elif code in delinq and delinq[code].get("pop"):
            pop = delinq[code]["pop"]
        if pop <= 0:
            continue
        pops[code] = pop

        en = enrich.get(code, {})
        rev = en.get("rev_med")
        pauv = en.get("tx_pauv")
        fam = maires[code]["f"] if code in maires and "f" in maires[code] else None

        if rev is None and pauv is None:
            continue

        vectors[code] = {
            "log_pop": math.log(pop),
            "rev_med": rev,
            "tx_pauv": pauv,
            "famille": fam,
        }

    print(f"  {len(vectors)} communes with feature vectors", file=sys.stderr)

    # Compute z-scores
    rev_vals = [v["rev_med"] for v in vectors.values() if v["rev_med"] is not None]
    pauv_vals = [v["tx_pauv"] for v in vectors.values() if v["tx_pauv"] is not None]
    logpop_vals = [v["log_pop"] for v in vectors.values()]

    lp_mean, lp_std = mean_std(logpop_vals)
    rev_mean, rev_std = mean_std(rev_vals)
    pauv_mean, pauv_std = mean_std(pauv_vals)

    for v in vectors.values():
        v["lp_z"] = (v["log_pop"] - lp_mean) / lp_std
        v["rev_z"] = (v["rev_med"] - rev_mean) / rev_std if v["rev_med"] is not None else 0.0
        v["pauv_z"] = (v["tx_pauv"] - pauv_mean) / pauv_std if v["tx_pauv"] is not None else 0.0

    # Step 2: Find nearest peers (unrolled distance for perf in tight loop)
    def distance(a, b):
        d = (W_LOG_POP * (a["lp_z"] - b["lp_z"]) ** 2 +
             W_REV * (a["rev_z"] - b["rev_z"]) ** 2 +
             W_PAUV * (a["pauv_z"] - b["pauv_z"]) ** 2)
        if a["famille"] and b["famille"] and a["famille"] == b["famille"]:
            d += FAMILY_BONUS
        return max(d, 0.0)

    codes_list = list(vectors.keys())
    print(f"  Computing peer groups for {len(codes_list)} communes...", file=sys.stderr)

    peers = {}
    for i, code in enumerate(codes_list):
        if (i + 1) % 5000 == 0:
            print(f"    {i + 1}/{len(codes_list)}...", file=sys.stderr)
        va = vectors[code]
        dists = []
        for other in codes_list:
            if other == code:
                continue
            d = distance(va, vectors[other])
            dists.append((d, other))
        peers[code] = [c for _, c in heapq.nsmallest(N_PEERS, dists)]

    # Step 3: Compute benchmarks and flags
    print("  Computing benchmarks and flags...", file=sys.stderr)

    def pm_ratio(code):
        """Compute PM+ASVP ratio per 10k, or None. Uses raw counts (not surv['r']) to avoid RATIO_CAP=50."""
        s = surv.get(code)
        p = pops.get(code, 0)
        if not s or p <= 0:
            return None
        return ((s.get("pm", 0) + s.get("asvp", 0)) / p) * 10000

    def accident_ratio(code):
        """Compute accidents per 10k for a commune, or None."""
        acc = prosp.get(code, {}).get("accidents")
        p = pops.get(code, 0)
        if acc is None or p <= 0:
            return None
        return acc / p * 10000

    pm_ratios = {c: pm_ratio(c) for c in codes_list}
    acc_ratios = {c: accident_ratio(c) for c in codes_list}

    result = {}

    for code in codes_list:
        peer_codes = peers[code]
        if not peer_codes:
            continue

        rec = {}
        top5 = peer_codes[:5]
        rec["peers"] = top5
        rec["peer_names"] = []
        for pc in top5:
            name = maires[pc].get("n", pc) if pc in maires else pc
            rec["peer_names"].append(name or pc)

        # Benchmarks via shared helper
        bench = {}

        b = compute_bench(
            delinq.get(code, {}).get("r"),
            [delinq[pc]["r"] for pc in peer_codes if pc in delinq and "r" in delinq[pc]])
        if b:
            bench["crime_r"] = b

        b = compute_bench(pm_ratios[code], [pm_ratios[pc] for pc in peer_codes])
        if b:
            bench["pm_r"] = b

        b = compute_bench(acc_ratios[code], [acc_ratios[pc] for pc in peer_codes])
        if b:
            bench["accidents_r"] = b

        b = compute_bench(
            enrich.get(code, {}).get("rev_med"),
            [enrich[pc]["rev_med"] for pc in peer_codes if pc in enrich and "rev_med" in enrich[pc]],
            round_digits=0)
        if b:
            bench["rev_med"] = b

        b = compute_bench(
            enrich.get(code, {}).get("tx_pauv"),
            [enrich[pc]["tx_pauv"] for pc in peer_codes if pc in enrich and "tx_pauv" in enrich[pc]])
        if b:
            bench["tx_pauv"] = b

        b = compute_bench(
            enrich.get(code, {}).get("dgf_hab"),
            [enrich[pc]["dgf_hab"] for pc in peer_codes if pc in enrich and "dgf_hab" in enrich[pc]])
        if b:
            bench["dgf_hab"] = b

        rec["bench"] = bench

        # Narrative flags
        flags = {}
        if "crime_r" in bench:
            flags["crime_above_peers"] = bench["crime_r"]["pct"] > PCT_CRIME_ABOVE

        has_pm = code in surv and (surv[code].get("pm", 0) + surv[code].get("asvp", 0)) > 0
        peers_with_pm = sum(1 for pc in peer_codes if pc in surv and (surv[pc].get("pm", 0) + surv[pc].get("asvp", 0)) > 0)
        peers_pm_pct = round(peers_with_pm / len(peer_codes) * 100) if peer_codes else 0
        flags["no_pm_peers_have"] = (not has_pm) and peers_pm_pct > PCT_PEERS_PM_MAJORITY
        flags["peers_pm_pct"] = peers_pm_pct

        has_vv = prosp.get(code, {}).get("videoverb", False)
        peers_with_vv = sum(1 for pc in peer_codes if prosp.get(pc, {}).get("videoverb", False))
        peers_vv_pct = round(peers_with_vv / len(peer_codes) * 100) if peer_codes else 0
        flags["no_vv_peers_have"] = (not has_vv) and peers_vv_pct > PCT_PEERS_VV_SIGNIFICANT
        flags["peers_vv_pct"] = peers_vv_pct

        pm_trend = prosp.get(code, {}).get("pm_trend", [])
        flags["pm_growing"] = len(pm_trend) >= 2 and pm_trend[-1] > pm_trend[0]

        if "accidents_r" in bench:
            flags["high_accident_rate"] = bench["accidents_r"]["pct"] > PCT_ACCIDENT_ABOVE

        if "dgf_hab" in bench:
            flags["budget_capacity"] = bench["dgf_hab"]["pct"] > 50

        if "tx_pauv" in bench:
            flags["high_poverty"] = bench["tx_pauv"]["pct"] > PCT_POVERTY_HIGH

        peers_with_sp = sum(1 for pc in peer_codes if prosp.get(pc, {}).get("stat_payant", False))
        flags["peers_stat_payant_pct"] = round(peers_with_sp / len(peer_codes) * 100) if peer_codes else 0

        rec["flags"] = flags
        result[code] = rec

    output_path = os.path.join(base, "insights.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(output_path) / 1024
    print(f"\nOutput: {output_path} ({size_kb:.0f} KB)", file=sys.stderr)
    print(f"  {len(result)} communes with insights", file=sys.stderr)

    if "11069" in result:
        print(f"\n  Sample (Carcassonne 11069):", file=sys.stderr)
        print(json.dumps(result["11069"], indent=2, ensure_ascii=False), file=sys.stderr)
    elif "75056" in result:
        print(f"\n  Sample (Paris 75056):", file=sys.stderr)
        print(json.dumps(result["75056"], indent=2, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
