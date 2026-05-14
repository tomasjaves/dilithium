# Dilithium - Kleptographic Backdoor Implementation

This repository contains a modified implementation of Dilithium (standardized as FIPS 204) that demonstrates a kleptographic backdoor in the signing process. It includes both the reference implementation (`ref/`) and the AVX2-optimized implementation (`avx2/`), plus benchmarking and detection tooling.

The backdoor alters signature generation so that the signer leaks the secret seed through the least significant bits of the first polynomial in `z`. The signature remains mathematically valid because the implementation restores the manipulated values before verification.

---

## 1. Project Structure

- `ref/`: reference implementation.
- `avx2/`: AVX2-optimized implementation.
- `benchmarks/`: timing, memory, and plotting scripts.
- `hypothesis_tests/`: statistical detection pipeline.
- `ml_detection/`: machine learning detection pipeline.

## 2. Overview

The project is organized around three goals:

1. Show how a kleptographic attack can be embedded into Dilithium.
2. Measure its impact through benchmark scripts and plots.
3. Detect the backdoor using statistical tests and machine learning.

## 3. Attack Summary

The attack works in three steps:

1. During signing, the implementation modifies the least significant bits of `z->vec[0]` to encode bits of the secret seed.
2. An attacker can recover the hidden seed directly from the manipulated signature.
3. Before verification, an internal `restore` routine reconstructs the honest signature so the standard verifier still accepts it.

> **Note:** When the backdoor is enabled, Dilithium runs in deterministic mode to keep the attack stable.

## 3. Requirements

- Linux or WSL on Windows.
- `make` and `gcc`.
- `python3` and `pip`.

## 4. Compilation and Usage

### Build the main binaries

Compile either implementation from its directory:

```bash
cd ref  # or cd avx2
make
```

This builds the normal test binaries, such as `test_dilithium2`.

### Backdoor flags

The backdoor is enabled by default. To build without it, pass:

```bash
CFLAGS="-DDILITHIUM_DISABLE_BACKDOOR" make
```

To silence the status output during the attack:

```bash
CFLAGS="-DDILITHIUM_SILENT_BACKDOOR" make
```

You can also disable it permanently by commenting out `#define DILITHIUM_ENABLE_BACKDOOR` in `ref/config.h` and `avx2/config.h`.

## 5. Benchmarking

The repository includes scripts to measure the impact of the backdoor across Dilithium modes 2, 3, and 5, in both the reference and AVX2 implementations.

### Run the full benchmark suite

```bash
./benchmarks/run_all.sh
```

You can restrict the run:

```bash
./benchmarks/run_all.sh ref
./benchmarks/run_all.sh avx2 5 bd
```

### Install analysis dependencies

```bash
pip3 install -r benchmarks/analysis/requirements.txt
```

### Generate plots and statistics

```bash
python3 benchmarks/analysis/plots.py
```

The script accepts:

- `--results`: root directory containing benchmark CSVs.
- `--out`: output directory for `stats.csv` and plots.

If the target directories do not exist, they are created automatically when needed.

Example:

```bash
python3 benchmarks/analysis/plots.py \
    --results benchmarks/results \
    --out benchmarks/analysis
```

### Benchmark outputs

The benchmark script creates `bench/` directories inside `ref/` and `avx2/` with binaries such as:

- `bench2_bd`, `bench3_bd`, `bench5_bd`
- `bench2_nobd`, `bench3_nobd`, `bench5_nobd`

Each binary writes raw CSV files for key generation, signing, and verification. The analysis step produces:

- `stats.csv`
- `plots/bar_total_time_ms.png`
- `plots/bar_cycles.png`
- `plots/bar_time_ms.png`
- `plots/bar_rss_kb.png`
- `plots/box_<impl>_D<mode>_<metric>.png`

## 6. Statistical Detection

The `hypothesis_tests/` directory contains a statistical pipeline that detects the backdoor by analyzing multiple signatures from the same keypair.

### 6.1 Dataset generation

`hypothesis_tests/dump_z.c` generates many signatures per keypair and stores the coefficients of `z[0]` in CSV format.

Build it from either implementation directory:

```bash
cd ref  # or cd avx2
make dump
```

This creates six binaries in `dump/`:

- `dump2_bd`, `dump3_bd`, `dump5_bd`
- `dump2_nobd`, `dump3_nobd`, `dump5_nobd`

Run them with no arguments:

```bash
./dump/dump2_bd
./dump/dump2_nobd
```

By default, each binary generates 5,000 keypairs with 50 signatures per keypair. You can change this with `NUM_KEYPAIRS` and `SIGS_PER_KEY`.

### 6.2 Statistical analysis

The analysis script applies two tests:

1. **Chi-squared test**: checks whether LSBs behave like fair bits across signatures.
2. **Variance test**: checks whether the LSBs remain constant when the backdoor is active.

Install dependencies:

```bash
pip3 install -r hypothesis_tests/requirements.txt
```

Run the analysis from the repository root:

```bash
python3 hypothesis_tests/hypothesis_tests.py \
    --original ref/dump/z_D2_nobd.csv \
    --backdoor ref/dump/z_D2_bd.csv
```

You can also run only one dataset:

```bash
python3 hypothesis_tests/hypothesis_tests.py --original ref/dump/z_D2_nobd.csv
python3 hypothesis_tests/hypothesis_tests.py --backdoor ref/dump/z_D2_bd.csv
```

Demo mode:

```bash
python3 hypothesis_tests/hypothesis_tests.py --demo
```

## 7. ML-Based Detection

The `ml_detection/` directory contains a machine learning pipeline that trains a Random Forest classifier to distinguish between original and backdoored implementations using the LSB distribution of `z[0]`.

### 7.1 Dataset generation

`ml_detection/generate_dataset.c` is similar to `dump_z.c`, but generates a larger dataset for training.

Build it from either implementation directory:

```bash
cd ref  # or cd avx2
make dataset
```

This creates six binaries in `ml_data/`:

- `gen2_bd`, `gen3_bd`, `gen5_bd`
- `gen2_nobd`, `gen3_nobd`, `gen5_nobd`

Run them with no arguments:

```bash
./ml_data/gen2_bd
./ml_data/gen2_nobd
```

To change the number of keypairs:

```bash
CFLAGS="-DNUM_KEYPAIRS=10000" make dataset
```

### 7.2 Training and evaluation

Install the Python dependencies:

```bash
pip3 install -r ml_detection/requirements.txt
```

Train the classifier:

```bash
python3 ml_detection/train_model.py \
    --original ref/ml_data/z_D2_nobd.csv \
    --backdoor ref/ml_data/z_D2_bd.csv
```

Adjust the test split if needed:

```bash
python3 ml_detection/train_model.py \
    --original ref/ml_data/z_D2_nobd.csv \
    --backdoor ref/ml_data/z_D2_bd.csv \
    --test-size 0.2
```

Demo mode:

```bash
python3 ml_detection/train_model.py --demo
```

The script prints accuracy, precision, recall, F1-score, a confusion matrix, and the top 10 most important coefficient positions.
It also prints the held-out split settings, class balance, and a majority-class baseline so the reported accuracy can be checked directly from the console output.
