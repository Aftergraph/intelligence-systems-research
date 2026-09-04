"""
Power analysis for STUDY-011.
Computes minimum per-cell N for McNemar test on binary FCR/VSR outcomes.
Derives from STUDY-008 simulation effect sizes as planning estimate.
"""
import math

# ─── Smallest Effects of Interest (SEOI) ───────────────────────────────────
# From STUDY-008 simulation:
#   FCR effect A vs G: Cohen's h = 1.671 (huge — likely inflated by simulation)
#   We use a CONSERVATIVE planning estimate: h = 0.5 (medium-large)
#   This is the SEOI: below this, the effect is not practically meaningful.

import math

# ─── Smallest Effects of Interest (SEOI) ───────────────────────────────────
SEOI_H = 0.5
ALPHA   = 0.01
POWER   = 0.80
CORRECTION_FACTOR = 3
ALPHA_ADJUSTED = ALPHA / CORRECTION_FACTOR   # = 0.00333

# ─── Normal quantile approximation (Beasley-Springer-Moro) ─────────────────
def norm_ppf(p):
    """Rational approximation to standard normal inverse CDF."""
    a = [2.515517, 0.802853, 0.010328]
    b = [1.432788, 0.189269, 0.001308]
    if p < 0.5:
        t = math.sqrt(-2 * math.log(p))
        sign = -1
    else:
        t = math.sqrt(-2 * math.log(1 - p))
        sign = 1
    num = a[0] + a[1]*t + a[2]*t*t
    den = 1 + b[0]*t + b[1]*t*t + b[2]*t*t*t
    return sign * (t - num / den)

def mcnemar_n(h, alpha, power):
    za = norm_ppf(1 - alpha / 2)
    zb = norm_ppf(power)
    return math.ceil((za + zb) ** 2 / h ** 2)


# Primary: unadjusted alpha (each hypothesis tested at ALPHA=0.01)
n_unadj = mcnemar_n(SEOI_H, ALPHA, POWER)
# Bonferroni-adjusted
n_adj   = mcnemar_n(SEOI_H, ALPHA_ADJUSTED, POWER)

print("=" * 60)
print("STUDY-011 POWER ANALYSIS")
print("=" * 60)
print(f"Smallest Effect of Interest (Cohen's h): {SEOI_H}")
print(f"Target power: {POWER:.0%}")
print(f"Alpha (per-hypothesis): {ALPHA}")
print(f"Bonferroni-adjusted alpha (3 hypotheses): {ALPHA_ADJUSTED:.5f}")
print()
print(f"Min N per cell (unadjusted α={ALPHA}): {n_unadj}")
print(f"Min N per cell (Bonferroni α={ALPHA_ADJUSTED:.4f}): {n_adj}")
print()

# ─── Study Design ──────────────────────────────────────────────────────────
# Confirmatory conditions: A, C, F, G (4 conditions)
# Provider strata: Dialagram, OpenRouter (2 zero-cost strata)
# [Phase 2, pending approval: OpenAI direct, Anthropic direct, Google direct]

CONDITIONS     = 4     # A, C, F, G
PROVIDERS_P1   = 2     # Dialagram + OpenRouter (zero-cost)
PROVIDERS_P2   = 3     # OpenAI + Anthropic + Google (paid, pending approval)
N_PER_CELL     = n_adj  # conservative: Bonferroni-adjusted

# Note: pairs for McNemar are within-workload pairs across conditions
# We plan N_PER_CELL LIVE_VALID per (provider × condition) cell
# Each workload serves as a matched pair across conditions within same provider

LIVE_VALID_TARGET_P1 = CONDITIONS * PROVIDERS_P1 * N_PER_CELL
LIVE_VALID_TARGET_P2 = CONDITIONS * PROVIDERS_P2 * N_PER_CELL

EXPECTED_SUCCESS_RATE = 0.75  # conservative: 75% of attempts yield LIVE_VALID
PLANNED_ATTEMPTS_P1 = math.ceil(LIVE_VALID_TARGET_P1 / EXPECTED_SUCCESS_RATE)
PLANNED_ATTEMPTS_P2 = math.ceil(LIVE_VALID_TARGET_P2 / EXPECTED_SUCCESS_RATE)

print("─" * 60)
print("DESIGN: Phase 1 (Zero-Cost)")
print(f"  Conditions: {CONDITIONS} (A, C, F, G)")
print(f"  Provider strata: {PROVIDERS_P1} (Dialagram, OpenRouter free)")
print(f"  N per cell target: {N_PER_CELL} LIVE_VALID")
print(f"  Total LIVE_VALID target: {LIVE_VALID_TARGET_P1}")
print(f"  Expected success rate: {EXPECTED_SUCCESS_RATE:.0%}")
print(f"  Planned attempts: {PLANNED_ATTEMPTS_P1}")
print()
print("DESIGN: Phase 2 (Paid — Pending Owner Approval)")
print(f"  Additional provider strata: {PROVIDERS_P2} (OpenAI, Anthropic, Google)")
print(f"  Total LIVE_VALID target: {LIVE_VALID_TARGET_P2}")
print(f"  Planned attempts: {PLANNED_ATTEMPTS_P2}")
print()
print("─" * 60)
print("COMBINED (Phase 1 + Phase 2):")
total_providers = PROVIDERS_P1 + PROVIDERS_P2
total_live_valid = CONDITIONS * total_providers * N_PER_CELL
total_attempts = math.ceil(total_live_valid / EXPECTED_SUCCESS_RATE)
print(f"  Provider strata: {total_providers}")
print(f"  Total LIVE_VALID target: {total_live_valid}")
print(f"  Planned attempts: {total_attempts}")
print()
print("=" * 60)
print("FORMULA VERIFICATION:")
print(f"  {CONDITIONS} conditions × {total_providers} providers × {N_PER_CELL} LIVE_VALID")
print(f"  = {total_live_valid} LIVE_VALID minimum")
print(f"  / {EXPECTED_SUCCESS_RATE:.0%} success rate")
print(f"  = {total_attempts} planned attempts")
print("=" * 60)
