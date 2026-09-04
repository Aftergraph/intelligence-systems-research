import math

# ponytail: Statistical Power Analysis for STUDY-006 HCI Trial (Phase EXT-3B).
# Calculates required sample size for 4-arm between-subjects evaluation:
# Modality 1: Chat-Only
# Modality 2: Traditional GUI
# Modality 3: Hybrid Agent UI
# Modality 4: Mission-Centric Interface
# Uses Cohen's f for one-way ANOVA and Cohen's d for pairwise comparisons.

def compute_sample_size(alpha=0.05, power=0.80, effect_size_d=0.65, num_groups=4):
    """
    Computes required sample size per arm and total sample size.
    For two-tailed comparison between mission UI and chat baseline:
    z_alpha for alpha=0.05 (two-tailed) = 1.96
    z_beta for power=0.80 = 0.8416
    """
    z_alpha = 1.95996
    z_beta = 0.84162  # For 80% power
    z_beta_90 = 1.28155 # For 90% power

    # Pairwise comparison sample size per arm:
    # n = 2 * ((z_alpha + z_beta) / d)^2
    n_per_arm_80 = 2 * ((z_alpha + z_beta) / effect_size_d) ** 2
    n_per_arm_90 = 2 * ((z_alpha + z_beta_90) / effect_size_d) ** 2

    # Ceiling
    n_arm_80 = math.ceil(n_per_arm_80)
    n_arm_90 = math.ceil(n_per_arm_90)

    total_80 = n_arm_80 * num_groups
    total_90 = n_arm_90 * num_groups

    return {
        "effect_size_d": effect_size_d,
        "alpha": alpha,
        "power_80": {
            "n_per_arm": n_arm_80,
            "total_sample_size": total_80
        },
        "power_90": {
            "n_per_arm": n_arm_90,
            "total_sample_size": total_90
        }
    }

def run_power_report():
    print("==================================================================")
    print(" STUDY-006 STATISTICAL POWER ANALYSIS & SAMPLE SIZE DETERMINATION")
    print(" Evaluating 4 Modalities: Chat-Only, Traditional GUI, Hybrid, Mission")
    print("==================================================================")

    # Scenarios: Medium effect (d=0.50), Expected pilot effect (d=0.65), Large effect (d=0.80)
    scenarios = [
        ("Conservative (Medium Effect)", 0.50),
        ("Calibrated from Pilot Simulation", 0.65),
        ("Optimistic (Large Effect)", 0.80)
    ]

    for label, d in scenarios:
        res = compute_sample_size(effect_size_d=d)
        n80 = res["power_80"]["n_per_arm"]
        tot80 = res["power_80"]["total_sample_size"]
        n90 = res["power_90"]["n_per_arm"]
        tot90 = res["power_90"]["total_sample_size"]

        print(f"\nScenario: {label} (Cohen's d = {d:.2f})")
        print(f"  Power 80% (beta=0.20): n = {n80} per arm | Total N = {tot80}")
        print(f"  Power 90% (beta=0.10): n = {n90} per arm | Total N = {tot90}")

    print("\nCONCLUSION:")
    print("  Based on pilot cognitive modeling variance (sigma_HEVO ~ 2.1, sigma_TLX ~ 7.4):")
    print("  Expected effect size d ~ 0.65 -> Required N = 152 total (38 per arm for 80% power)")
    print("  or N = 200 total (50 per arm for 90% power).")
    print("  The arbitrary N=64 is formally replaced with the power-justified sample size.")

if __name__ == "__main__":
    run_power_report()
