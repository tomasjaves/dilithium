"""
ML-based backdoor detection for CRYSTALS-Dilithium (ML-DSA).

Trains a Random Forest classifier to distinguish between original and
backdoored implementations based on LSB proportion vectors extracted
from the z[0] polynomial coefficients across multiple signatures.

Usage:
    python3 train_model.py \
        --original <impl>/ml_data/z_D2_nobd.csv \
        --backdoor <impl>/ml_data/z_D2_bd.csv

    python3 train_model.py --demo
"""

import argparse
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

N_COEFFS = 256


def load_and_extract_features(csv_path, label):
    """
    Load a CSV of z[0] coefficients and compute, for each keypair,
    the 256-dimensional LSB proportion vector.

    Returns (X, y) where X has shape (n_keypairs, 256) and y is the label.
    """
    df = pd.read_csv(csv_path)
    coeff_cols = [f"coeff_{i}" for i in range(N_COEFFS)]
    coeffs = df[coeff_cols].values
    lsbs = np.abs(coeffs) % 2

    keypair_ids = df["keypair_id"].values
    unique_kps = np.unique(keypair_ids)

    X = np.zeros((len(unique_kps), N_COEFFS))
    for idx, kp in enumerate(unique_kps):
        mask = keypair_ids == kp
        X[idx] = lsbs[mask].mean(axis=0)

    y = np.full(len(unique_kps), label)
    return X, y


def generate_synthetic(n_keypairs=5000, n_sigs=50):
    """Generate synthetic data for demo mode."""
    gamma1 = 2**17
    X_orig = np.zeros((n_keypairs, N_COEFFS))
    X_bd = np.zeros((n_keypairs, N_COEFFS))

    for kp in range(n_keypairs):
        # Original: random LSBs -> proportions ~0.5
        lsbs = np.random.randint(0, 2, size=(n_sigs, N_COEFFS))
        X_orig[kp] = lsbs.mean(axis=0)

        # Backdoored: LSBs fixed to seed bits -> proportions = 0 or 1
        seed_bits = np.random.randint(0, 2, size=N_COEFFS)
        X_bd[kp] = seed_bits.astype(float)

    X = np.vstack([X_orig, X_bd])
    y = np.array([0] * n_keypairs + [1] * n_keypairs)
    return X, y


def main():
    parser = argparse.ArgumentParser(
        description="Train a Random Forest to detect kleptographic backdoor in ML-DSA"
    )
    parser.add_argument("--original", type=str,
                        help="CSV of original (clean) z[0] coefficients")
    parser.add_argument("--backdoor", type=str,
                        help="CSV of backdoored z[0] coefficients")
    parser.add_argument("--demo", action="store_true",
                        help="Use synthetic data (no CSVs required)")
    parser.add_argument("--test-size", type=float, default=0.3,
                        help="Fraction of data reserved for testing (default: 0.3)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    args = parser.parse_args()

    if args.demo:
        print("Demo mode: generating synthetic data...")
        print("  5000 keypairs x 50 signatures per class\n")
        X, y = generate_synthetic(n_keypairs=5000, n_sigs=50)
    elif args.original and args.backdoor:
        print(f"Loading original:   {args.original}")
        X_orig, y_orig = load_and_extract_features(args.original, label=0)
        print(f"  -> {len(y_orig)} keypairs")

        print(f"Loading backdoored: {args.backdoor}")
        X_bd, y_bd = load_and_extract_features(args.backdoor, label=1)
        print(f"  -> {len(y_bd)} keypairs\n")

        X = np.vstack([X_orig, X_bd])
        y = np.concatenate([y_orig, y_bd])
    else:
        parser.print_help()
        print("\nExample:")
        print("  python3 train_model.py --original ref/ml_data/z_D2_nobd.csv --backdoor ref/ml_data/z_D2_bd.csv")
        print("  python3 train_model.py --demo")
        sys.exit(1)

    # --- Train/Test Split ---
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    print(f"Dataset:  {len(y)} samples ({sum(y == 0)} original, {sum(y == 1)} backdoored)")
    print(f"Training: {len(y_train)} samples")
    print(f"Testing:  {len(y_test)} samples")
    print()
    print(f"Evaluation: held-out test split (stratified, seed={args.seed}, test_size={args.test_size})")
    print(f"Training class balance: {np.sum(y_train == 0)} original / {np.sum(y_train == 1)} backdoored")
    print(f"Testing  class balance: {np.sum(y_test == 0)} original / {np.sum(y_test == 1)} backdoored")
    print()

    # --- Train Random Forest ---
    clf = RandomForestClassifier(
        n_estimators=100,
        random_state=args.seed,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    # --- Evaluate ---
    y_pred = clf.predict(X_test)
    majority_class = int(np.bincount(y_train).argmax())
    baseline_pred = np.full_like(y_test, majority_class)
    baseline_acc = accuracy_score(y_test, baseline_pred)
    model_acc = accuracy_score(y_test, y_pred)

    print("=" * 50)
    print("  RESULTS")
    print("=" * 50)
    print()
    print(f"  Majority-class baseline accuracy: {baseline_acc:.4f}")
    print(f"  Model accuracy:                  {model_acc:.4f}")
    print(f"  Accuracy lift over baseline:     {model_acc - baseline_acc:+.4f}\n")

    print("  Classification Report:")
    target_names = ["Original", "Backdoored"]
    print(classification_report(y_test, y_pred, target_names=target_names))

    print("  Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"                  Predicted Orig  Predicted BD")
    print(f"  Actual Orig     {cm[0][0]:>13}  {cm[0][1]:>12}")
    print(f"  Actual BD       {cm[1][0]:>13}  {cm[1][1]:>12}")

    # --- Feature Importance (top 10) ---
    importances = clf.feature_importances_
    top_indices = np.argsort(importances)[::-1][:10]
    print(f"\n  Top 10 coefficient positions that helped the model the most:")
    for rank, idx in enumerate(top_indices, 1):
        print(f"    {rank:>2}. coeff_{idx:<3}  importance: {importances[idx]:.4f}")

    print()


if __name__ == "__main__":
    main()
