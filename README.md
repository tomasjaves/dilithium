# Dilithium - Kleptographic Backdoor Implementation

This repository contains a C implementation of the **Dilithium** signature scheme (standardized as [FIPS 204](https://csrc.nist.gov/pubs/fips/204/final)), modified to include a **Kleptographic Backdoor**. This project has been developed as part of a Bachelor's Thesis (TFG).

The reference implementation (`ref/`) and the AVX2-optimized implementation (`avx2/`) have been modified to demonstrate how a stealthy kleptographic attack can be embedded into the signing process to exfiltrate the secret key seed, while maintaining the mathematical validity of the signatures.

---

## 1. Abstract

This project focuses on the analysis and implementation of a kleptographic attack on Dilithium, a lattice-based post-quantum signature scheme. The attack modifies the signature generation procedure so that the generated signatures leak information about the underlying secret seed without corrupting the standard verification process.

## 2. Introduction to the Attack

A kleptographic attack allows an adversary to secretly extract cryptographic keys through an apparently secure communication channel. In the context of Dilithium, the attack works as follows:

1. **Seed Exfiltration (During Signing):** The signature generation process is manipulated right after computing the signature vector `z`. The algorithm directly modifies the least significant bits of the first polynomial in `z` (`z->vec[0]`) to encode the bits of the secret `seed`.
2. **Recovery (By the Attacker):** An attacker intercepting the signature can easily extract the hidden bits directly from the manipulated vector `z` and fully recover the original `seed`, effectively compromising the signer's secret key.
3. **Signature Restoration (To Pass Verification):** If a signature is manipulated, it would normally fail the standard verification. To prevent this, the attacker uses an internal `restore` function before the actual verification step. Using the recovered `seed`, the attacker re-derives the private key elements (like `s1` and `rho'`). Then, it iterates through possible values of the counter `kappa` (the nonce) to perfectly reconstruct the original masking vector `y`. With the correct `y`, the honest `z` is recomputed and matched against the untouched parts of the transmitted `z`. Once a match is found, the manipulated parts of `z` are restored to their original honest values, allowing the standard verification to succeed as if nothing had happened.

> **Note:** When the backdoor is enabled, Dilithium operates in deterministic mode (disabling `DILITHIUM_RANDOMIZED_SIGNING`) to ensure the attack's stability.

## 3. Compilation and Usage

### Requirements
- A Linux environment (or WSL on Windows).
- `make`, `gcc`.
- `python3` and `pip` (for benchmarking analysis).

### Compilation
To compile the standalone test programs for either the `ref` or `avx2` implementation:
```bash
cd ref  # or cd avx2
make
```
This will produce the standard test binaries such as `test_dilithium2`. 

**Compilation Flags:**
The backdoor is **enabled by default**. To compile the binaries without the backdoor (for comparison purposes), you can inject the flag via the `CFLAGS` environment variable before running `make`:

```bash
# Disable the backdoor
CFLAGS="-DDILITHIUM_DISABLE_BACKDOOR" make

# Silence the backdoor status output (useful for benchmarking)
CFLAGS="-DDILITHIUM_SILENT_BACKDOOR" make
```

*Alternatively, you can permanently disable it by commenting out `#define DILITHIUM_ENABLE_BACKDOOR` inside `ref/config.h` and `avx2/config.h`.*

## 4. Benchmarking

This repository includes an automated benchmarking suite designed to measure the impact of the backdoor across all security levels (Dilithium 2, 3, and 5) and implementations (AVX2 and Reference).

### Running the Benchmarks and Generating Plots
A shell script orchestrates the compilation and execution of 12 different benchmark binaries (10,000 iterations each). To run the full suite and immediately process the raw data into human-readable statistics and plots, execute:

```bash
./benchmarks/run_all.sh
```

The script accepts up to three positional arguments to filter the execution:
```bash
bash benchmarks/run_all.sh ref             # only the reference implementation
bash benchmarks/run_all.sh avx2 5 bd       # only avx2, Dilithium5, backdoor enabled
```

For tighter measurements on Linux, consider pinning the process to a single core (`taskset -c 3 bash benchmarks/run_all.sh`), setting the CPU governor to performance mode (`sudo cpupower frequency-set -g performance`), and closing other workloads.

After the script finishes, you need to install the Python dependencies for the analysis tools. Execute the following command:

```bash
pip3 install -r benchmarks/analysis/requirements.txt
```

Finally, generate the statistics and plots with:

```bash
python3 benchmarks/analysis/plots.py
```

The script accepts `--results` to specify the root directory containing the benchmark CSVs (defaults to `benchmarks/results/`) and `--out` to set the output directory for `stats.csv` and the `plots/` folder (defaults to `benchmarks/analysis/`).

#### Intermediate Benchmark Binaries (`ref/bench/` and `avx2/bench/`)
When the script is executed, it automatically triggers a compilation process that generates a `bench/` directory inside both `ref/` and `avx2/`. These directories contain the isolated, standalone C binaries used to perform the measurements:
- `bench2_bd`, `bench3_bd`, `bench5_bd`: Binaries compiled **with** the kleptographic backdoor enabled for Dilithium modes 2, 3, and 5.
- `bench2_nobd`, `bench3_nobd`, `bench5_nobd`: Binaries compiled **without** the backdoor (using `-DDILITHIUM_DISABLE_BACKDOOR`) to serve as the control group.

These binaries internally execute 10,000 iterations (configurable via the `NTESTS` define) measuring cycles, timing, and memory, outputting the raw CSV files that are later consumed by the Python script. Each binary expects a single argument: the output directory where the CSVs will be written. CPU cycles are measured via `rdtsc` on x86-64 architectures, with a fallback to the monotonic clock on other platforms. Peak RSS is obtained through `getrusage`.

#### Raw Results Data (`benchmarks/results/`)
After the script finishes, the raw measurements are saved here. The script creates a hierarchical folder structure corresponding to the implementation, security mode, and backdoor presence (e.g., `benchmarks/results/avx2/Dilithium5/with_bd/`). 

Inside each of these specific directories, you will find four files:
- `keygen.csv`, `sign.csv`, `verify.csv`: The raw benchmark data for each phase containing 10,000 rows with columns `iter,cycles,time_ns,peak_rss_kb,ok`.
- `summary.csv`: Key-value pairs summarizing the run: algorithm name, backdoor status, number of tests, key/signature sizes in bytes, pass/fail counts per phase, peak RSS, and total wall time in nanoseconds.

#### Output of the Analysis (`benchmarks/analysis/`):
1. **`stats.csv`**: A comprehensive table containing the mean, median, standard deviation, and 95% Confidence Intervals (CI) for cycles, time (ms), and peak memory consumption (Peak RSS in KB), aggregated across all phases (KeyGen, Sign, Verify).
2. **`plots/` directory**:
   - `bar_total_time_ms.png`: A bar chart comparing the **total execution time** (KeyGen + Sign + Verify) per full iteration.
   - `bar_cycles.png` & `bar_time_ms.png`: Bar charts showing the average cycles and time separated by phase. The impact of the backdoor is clearly identifiable here: KeyGen remains unaltered (any variance is OS noise), Sign shows a very slight overhead due to the bitwise `embed` injection, and Verify shows a prominent overhead due to the computationally heavy `restore` process over `kappa`.
   - `bar_rss_kb.png`: A grouped bar chart comparing the Peak RSS (maximum RAM consumed), verifying empirically that the backdoor operates without causing suspicious memory spikes.
   - `box_<impl>_D<mode>_<metric>.png`: Boxplots visualizing the statistical distribution and variance of the execution cycles for each mode, allowing you to observe the exact impact of the attack's mathematical operations.

## 5. Statistical Countermeasure — Hypothesis Tests

This repository also includes a statistical detection pipeline that demonstrates how an auditor, given access to multiple signatures from the same keypair, can detect the presence of the kleptographic backdoor. The pipeline consists of two stages: data collection (C) and statistical analysis (Python).

### 5.1. Data Collection (`benchmarks/dump_z.c`)

`dump_z.c` generates multiple signatures per keypair and dumps the coefficients of the first polynomial of `z` (`z->vec[0]`) to a CSV file. This is the vector where the backdoor encodes the secret seed bits into the least significant bits.

The program signs random 59-byte messages using `crypto_sign_signature` (the standard signing function of the codebase). Whether the backdoor is active or not depends entirely on the compilation flags (see Section 3), not on any special function call. The output filename is determined automatically at compile time from `DILITHIUM_MODE` and `DILITHIUM_ENABLE_BACKDOOR`.

**Building and running:**
```bash
cd ref  # or cd avx2
make dump
```

This produces six binaries inside a `dump/` directory:
- `dump2_bd`, `dump3_bd`, `dump5_bd`: Compiled **with** the backdoor enabled.
- `dump2_nobd`, `dump3_nobd`, `dump5_nobd`: Compiled **without** the backdoor.

Each binary runs autonomously with no arguments:
```bash
./dump/dump2_bd      # → generates dump/z_D2_bd.csv
./dump/dump2_nobd    # → generates dump/z_D2_nobd.csv
```

By default, each binary generates 50 keypairs × 50 signatures per keypair = 2,500 rows. Each row contains the keypair ID, signature ID, and the 256 coefficients of `z[0]`. These parameters can be adjusted via `NUM_KEYPAIRS` and `SIGS_PER_KEY` defines.

**CSV format:**
```
keypair_id,signature_id,coeff_0,coeff_1,...,coeff_255
```
- `keypair_id`: Identifies which keypair produced the signature (0 to `NUM_KEYPAIRS-1`). A new key pair (public key + secret key) is generated for each ID.
- `signature_id`: Identifies which signature within that keypair (0 to `SIGS_PER_KEY-1`). Each signature corresponds to a different random message signed with the same key.

### 5.2. Statistical Analysis (`benchmarks/analysis/hypothesis_tests.py`)

This Python script applies two hypothesis tests to the collected CSV data. The core observation is: if the backdoor is active, the LSBs of `z[0]` are forced to match the seed bits ξ, so they remain **constant** across all signatures from the same keypair. Without the backdoor, LSBs vary randomly (Bernoulli p=0.5).

**Tests implemented:**

1. **Chi-squared test:** For each of the 256 coefficient positions, it counts how many times the LSB is 0 vs. 1 across all signatures of a keypair. Under the null hypothesis (no backdoor), the expected split is N/2 each. The individual χ² statistics are aggregated into a single test with 256 degrees of freedom. Bonferroni correction is applied for per-position significance.

2. **Variance test:** Computes the sample variance of the LSB at each position across signatures. Without the backdoor, the expected variance is ~0.25 (Bernoulli). With the backdoor, the variance is exactly 0.0 (all LSBs identical). A mean variance below 0.01 triggers detection.

**Running the analysis:**

First, install the dependencies (if not already installed):
```bash
pip3 install numpy scipy pandas
```

Then, run the script **from the repository root** pointing to the CSVs generated in the previous step. At least one of `--original` or `--backdoor` must be provided; they can be used independently or together:
```bash
# Analyze both datasets and compare results
python3 benchmarks/analysis/hypothesis_tests.py \
    --original ref/dump/z_D2_nobd.csv \
    --backdoor ref/dump/z_D2_bd.csv

# Analyze only the original (clean) signatures
python3 benchmarks/analysis/hypothesis_tests.py \
    --original ref/dump/z_D2_nobd.csv

# Analyze only the backdoored signatures
python3 benchmarks/analysis/hypothesis_tests.py \
    --backdoor ref/dump/z_D2_bd.csv
```

Alternatively, a demo mode generates synthetic data without requiring compilation:
```bash
python3 benchmarks/analysis/hypothesis_tests.py --demo
```

**Output:** The script prints a structured report per keypair group showing χ² statistics, variance means, detection counts, and a final summary with true positive and false positive rates.