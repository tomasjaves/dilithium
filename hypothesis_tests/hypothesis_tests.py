import argparse
import sys
import numpy as np
import pandas as pd
from scipy import stats

N_COEFFS = 256


def load_csv(csv_path):
    df = pd.read_csv(csv_path)
    return df


def extract_lsbs(df):
    coeff_cols = [f"coeff_{i}" for i in range(N_COEFFS)]
    coeffs = df[coeff_cols].values
    lsbs = np.abs(coeffs) % 2
    return lsbs


def chi_squared_test(lsbs_group, alpha=0.05):
    n_sigs = lsbs_group.shape[0]
    expected = np.array([n_sigs / 2.0, n_sigs / 2.0])

    chi2_vals = np.zeros(N_COEFFS)
    p_vals = np.zeros(N_COEFFS)

    for i in range(N_COEFFS):
        n_ones = np.sum(lsbs_group[:, i])
        n_zeros = n_sigs - n_ones
        observed = np.array([n_zeros, n_ones])
        chi2_stat, p_val = stats.chisquare(observed, expected)
        chi2_vals[i] = chi2_stat
        p_vals[i] = p_val

    chi2_total = np.sum(chi2_vals)
    p_total = 1.0 - stats.chi2.cdf(chi2_total, df=N_COEFFS)

    alpha_bonf = alpha / N_COEFFS
    n_significant = int(np.sum(p_vals < alpha_bonf))

    detected = p_total < alpha

    return {
        "chi2_per_position": chi2_vals,
        "p_per_position": p_vals,
        "n_significant": n_significant,
        "chi2_total": chi2_total,
        "p_total": p_total,
        "detected": detected,
    }


def variance_test(lsbs_group):
    n_sigs = lsbs_group.shape[0]
    if n_sigs < 2:
        return {
            "var_per_position": np.zeros(N_COEFFS),
            "mean_variance": 0.0,
            "n_zero_variance": N_COEFFS,
            "detected": True,
        }

    var_per_pos = np.var(lsbs_group, axis=0, ddof=1)
    mean_var = float(np.mean(var_per_pos))
    n_zero = int(np.sum(var_per_pos == 0.0))

    detected = mean_var < 0.01

    return {
        "var_per_position": var_per_pos,
        "mean_variance": mean_var,
        "n_zero_variance": n_zero,
        "detected": detected,
    }


def analyze_group(df, label):
    lsbs = extract_lsbs(df)
    results = []

    for kp_id in sorted(df["keypair_id"].unique()):
        kp_mask = (df["keypair_id"] == kp_id).values
        kp_lsbs = lsbs[kp_mask]

        if kp_lsbs.shape[0] < 2:
            continue

        chi2_result = chi_squared_test(kp_lsbs)
        var_result = variance_test(kp_lsbs)
        results.append({
            "keypair_id": kp_id,
            "n_signatures": kp_lsbs.shape[0],
            "chi2": chi2_result,
            "var": var_result,
        })

    return results


def print_report(results, label):
    if not results:
        print(f"\n  {label}: no data\n")
        return

    n_kp = len(results)
    n_sigs = results[0]["n_signatures"]

    chi2_totals = [r["chi2"]["chi2_total"] for r in results]
    chi2_detected = sum(1 for r in results if r["chi2"]["detected"])
    mean_vars = [r["var"]["mean_variance"] for r in results]
    var_detected = sum(1 for r in results if r["var"]["detected"])
    zero_vars = [r["var"]["n_zero_variance"] for r in results]

    crit_value = stats.chi2.ppf(0.95, df=N_COEFFS)

    print(f"\n{'='*64}")
    print(f"  {label}")
    print(f"{'='*64}")
    print(f"  Keypairs analyzed:      {n_kp}")
    print(f"  Signatures per keypair: {n_sigs}")

    print(f"\n  --- Chi-squared test (H0: LSBs independent across signatures) ---")
    print(f"  Aggregated chi2 (mean): {np.mean(chi2_totals):.1f}")
    print(f"  Aggregated chi2 (min):  {np.min(chi2_totals):.1f}")
    print(f"  Aggregated chi2 (max):  {np.max(chi2_totals):.1f}")
    print(f"  Critical value (256 df):{crit_value:.1f}")
    print(f"  Keypairs detected:      {chi2_detected}/{n_kp}")

    print(f"\n  --- Variance test (H0: var(LSB) ~ 0.25 per position) ---")
    print(f"  Mean variance (mean):   {np.mean(mean_vars):.6f}")
    print(f"  Mean variance (min):    {np.min(mean_vars):.6f}")
    print(f"  Mean variance (max):    {np.max(mean_vars):.6f}")
    print(f"  Expected value (H0):    ~0.25")
    print(f"  Positions var=0 (avg):  {np.mean(zero_vars):.1f}/256")
    print(f"  Keypairs detected:      {var_detected}/{n_kp}")
    print()

    return chi2_detected, var_detected


def print_summary(res_orig, res_bd, det_orig, det_bd):
    print("=" * 64)
    print("  SUMMARY")
    print("=" * 64)

    if res_orig:
        n = len(res_orig)
        fp_chi, fp_var = det_orig
        fp = sum(1 for r in res_orig
                 if r["chi2"]["detected"] or r["var"]["detected"])
        print(f"\n  False positives (original flagged as BD):         {fp}/{n}")
        print(f"    - By chi-squared: {fp_chi}/{n}")
        print(f"    - By variance:    {fp_var}/{n}")

    if res_bd:
        n = len(res_bd)
        tp_chi, tp_var = det_bd
        tp = sum(1 for r in res_bd
                 if r["chi2"]["detected"] or r["var"]["detected"])
        print(f"  True positives (BD correctly detected):           {tp}/{n}")
        print(f"    - By chi-squared: {tp_chi}/{n}")
        print(f"    - By variance:    {tp_var}/{n}")

    print()


def generate_synthetic(n_keypairs=30, n_sigs=50):
    gamma1 = 2**17
    rows_orig = []
    rows_bd = []

    for kp in range(n_keypairs):
        for s in range(n_sigs):
            coeffs = np.random.randint(-gamma1 + 1, gamma1 + 1, size=N_COEFFS)
            rows_orig.append([kp, s] + coeffs.tolist())

        seed_bits = np.random.randint(0, 2, size=N_COEFFS)
        for s in range(n_sigs):
            coeffs = np.random.randint(-gamma1 + 1, gamma1 + 1, size=N_COEFFS)
            for i in range(N_COEFFS):
                if abs(coeffs[i]) % 2 != seed_bits[i]:
                    coeffs[i] += 1 if seed_bits[i] == 0 else -1
            rows_bd.append([kp, s] + coeffs.tolist())

    cols = ["keypair_id", "signature_id"] + [f"coeff_{i}" for i in range(N_COEFFS)]
    df_orig = pd.DataFrame(rows_orig, columns=cols)
    df_bd = pd.DataFrame(rows_bd, columns=cols)
    return df_orig, df_bd


def main():
    parser = argparse.ArgumentParser(
        description="Hypothesis tests for kleptographic backdoor detection in ML-DSA"
    )
    parser.add_argument("--original", type=str,
                        help="CSV of original (clean) signatures")
    parser.add_argument("--backdoor", type=str,
                        help="CSV of compromised (backdoored) signatures")
    parser.add_argument("--demo", action="store_true",
                        help="Use synthetic data (no CSVs required)")
    args = parser.parse_args()

    if args.demo:
        print("Demo mode: generating synthetic data...")
        print("  30 keypairs x 50 signatures, original and compromised\n")
        df_orig, df_bd = generate_synthetic(n_keypairs=30, n_sigs=50)
    elif args.original or args.backdoor:
        df_orig = load_csv(args.original) if args.original else None
        df_bd = load_csv(args.backdoor) if args.backdoor else None
    else:
        parser.print_help()
        print("\nExample:")
        print("  python hypothesis_tests.py --original z_D2_nobd.csv --backdoor z_D2_bd.csv")
        print("  python hypothesis_tests.py --demo")
        sys.exit(1)

    if df_orig is not None:
        print(f"Original signatures:     {len(df_orig)}")
    if df_bd is not None:
        print(f"Compromised signatures:  {len(df_bd)}")

    res_orig = analyze_group(df_orig, "ORIGINAL") if df_orig is not None else []
    res_bd = analyze_group(df_bd, "BACKDOOR") if df_bd is not None else []

    det_orig = (0, 0)
    det_bd = (0, 0)
    if res_orig:
        det_orig = print_report(res_orig, "ORIGINAL SIGNATURES (no backdoor)")
    if res_bd:
        det_bd = print_report(res_bd, "COMPROMISED SIGNATURES (with backdoor)")

    print_summary(res_orig, res_bd, det_orig, det_bd)


if __name__ == "__main__":
    main()
