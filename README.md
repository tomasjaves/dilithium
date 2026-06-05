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
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`: containerised builds
  of both implementations (see §4).
- `Dockerfile.runtime`: slim multi-arch deployment image of `ref/` (≈120 MB,
  no toolchain, no Python) intended for IoT targets — see §4.

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

Choose one path:

**Native (Linux or WSL on Windows)**
- `make` and `gcc` (AVX2 build requires an x86_64 CPU with AVX2 + POPCNT).
- `python3` and `pip`.
- `libssl-dev` for the `nistkat` target in `ref/`.

**Docker (any host)**
- Docker Engine 24+ and Docker Compose v2.
- For the AVX2 image: x86_64 host with AVX2 + POPCNT support. The Compose
  service pins `platform: linux/amd64`.

See §4 for both build paths.

## 4. Compilation and Usage

### Build the main binaries (native)

Compile either implementation from its directory:

```bash
cd ref  # or cd avx2
make
```

This builds the normal test binaries, such as `test_dilithium2`.

### Build the main binaries (Docker)

Both implementations are also packaged as separate images via a single
`Dockerfile` parameterised by the `IMPL` build arg. The repository ships a
`docker-compose.yml` that defines two services: `ref` and `avx2`.

```bash
# Build both images (dilithium-ref:latest, dilithium-avx2:latest)
docker compose build

# Drop into a shell with everything ready to compile and run
docker compose run --rm ref     # working dir: /src/ref
docker compose run --rm avx2    # working dir: /src/avx2

# Run a Makefile target directly
docker compose run --rm ref  make speed
docker compose run --rm avx2 make speed
docker compose run --rm ref  make nistkat
```

The repository is bind-mounted into `/src`, so edits on the host are visible
inside the container and any generated `bench/`, `dump/`, `ml_data/`, or
`output/` directories persist on disk. The image already includes `gcc`,
`make`, `libssl-dev`, and a Python virtualenv with the dependencies from
`hypothesis_tests/requirements.txt`, `ml_detection/requirements.txt`, and
`benchmarks/analysis/requirements.txt`, so the Python tooling described in
§5–§7 also works inside the container without further setup.

#### Security posture

Both services run with defence-in-depth enabled by default:

| Setting                       | Effect                                              |
|-------------------------------|-----------------------------------------------------|
| `user: "1000:1000"` + `USER`  | No root inside the container.                       |
| `read_only: true`             | Root filesystem immutable.                          |
| `tmpfs: /tmp`, `HOME=/tmp`    | Only `/tmp` (and the bind-mounted `/src`) writable. |
| `cap_drop: [ALL]`             | All Linux capabilities dropped (`CapEff=0`).        |
| `no-new-privileges:true`      | Setuid escalation blocked.                          |
| `network_mode: none`          | No outbound network at runtime.                     |
| `init: true`                  | Proper PID 1 / zombie reaping.                      |

Overrides for the rare cases that need them:

```bash
# Need network (e.g. ad-hoc pip install) for a single invocation:
docker compose run --rm --network bridge ref pip install --user <pkg>

# Host UID/GID is not 1000 (Linux hosts only — Docker Desktop on Windows /
# macOS maps bind-mount ownership automatically). Rebuild with matching IDs:
docker compose build \
    --build-arg APP_UID=$(id -u) \
    --build-arg APP_GID=$(id -g)
# Then edit `user: "<uid>:<gid>"` in docker-compose.yml to match.
```

#### Notes and caveats

- The `avx2` service requires an x86_64 host with AVX2; on non-AMD64 hosts
  the image must be run through emulation and the runtime CPU still needs
  the relevant ISA extensions.
- `avx2/` uses git symlinks pointing into `ref/`. They are stripped from the
  build context via `.dockerignore` and recreated inside the image to avoid a
  BuildKit symlink-handling bug on Windows hosts. The bind mount at runtime
  exposes the original symlinks as-is.
- The bind mount at `/src` overlays the binaries that `RUN make all` built
  into the image. After `docker compose build`, run `make all` once inside
  each container so the host filesystem ends up with usable binaries:

  ```bash
  docker compose run --rm ref  make all
  docker compose run --rm avx2 make all
  ```

#### Slim runtime image for IoT deployment (`ref-slim`)

The fat `dilithium-ref` / `dilithium-avx2` images carry the toolchain and the
full Python analysis stack (≈1.3 GB), which is appropriate for development
but oversized for an IoT target. A separate `Dockerfile.runtime` produces a
**slim multi-arch runtime image (≈120 MB)** that contains only the compiled
C binaries for the reference implementation. Enough to demonstrate the
backdoor end-to-end on a low-resource device; the backdoor is active by
default, identical to the fat image.

What it ships (9 binaries under `/opt/dilithium/bin`):

- `test_dilithium{2,3,5}`  — sign/verify smoke; prints recovered seed
  (end-to-end backdoor proof)
- `test_vectors{2,3,5}`    — KAT vector generation
- `PQCgenKAT_sign{2,3,5}`  — NIST KAT generator (linked against `libcrypto`)

What it omits:

- The toolchain (`gcc`, `make`, `libssl-dev`).
- The Python virtualenv and ML dependencies.
- `test_speed{2,3,5}` and `test_mul`: rely on `rdtsc` (x86-only); cannot be
  built for `linux/arm64` / `linux/arm/v7` and have no purpose on an IoT
  target where you would not run the microbenchmarks.
- `dump{2,3,5}_{bd,nobd}` and `gen{2,3,5}_{bd,nobd}` (statistical / ML
  dataset generators): these are inputs to the Python analysis pipelines
  (`hypothesis_tests.py`, `train_model.py`) which live in the fat image, so
  pairing them with the slim runtime would force a split workflow without
  saving anything. Use the fat image when you need the §6/§7 experiments.

Single-arch build (current host architecture):

```bash
docker compose build ref-slim
# or
docker build -f Dockerfile.runtime -t dilithium-ref-slim:latest .
```

Multi-arch build (`amd64` + `arm64` + `armv7`) via Buildx, pushed to a registry:

```bash
docker buildx create --use --name dilithium-mab
docker buildx build -f Dockerfile.runtime \
    --platform linux/amd64,linux/arm64,linux/arm/v7 \
    -t <registry>/dilithium-ref-slim:latest --push .
```

Offline deployment (no registry — build a single-arch tarball on the dev
machine, `scp` to the IoT target, load locally):

```bash
# On the PC — pick the target arch (linux/arm64 for RPi 4/5, Jetson Nano;
# linux/arm/v7 for RPi Zero / RPi 2)
docker buildx build -f Dockerfile.runtime --platform linux/arm64 \
    -t dilithium-ref-slim:arm64 --output type=docker .
docker save dilithium-ref-slim:arm64 | gzip > slim-arm64.tar.gz
scp slim-arm64.tar.gz pi@raspberrypi.local:~

# On the IoT device
gunzip -c slim-arm64.tar.gz | docker load
docker run --rm dilithium-ref-slim:arm64 test_dilithium2
```

Run a binary directly. The image self-documents under `docker run` with no
args (lists `/opt/dilithium/bin`); override with the binary name:

```bash
docker run --rm dilithium-ref-slim                       # lists binaries
docker run --rm dilithium-ref-slim test_dilithium2       # sign/recover smoke
docker run --rm -v "$PWD/out:/tmp" dilithium-ref-slim \
    PQCgenKAT_sign2                                       # KAT into ./out
```

The slim image keeps the same defence-in-depth posture as the fat one
(non-root `dilithium` user, no shell home, `libssl3` as the only runtime
dependency) and the `ref-slim` Compose service inherits the same hardening
anchor (`read_only`, `cap_drop: ALL`, `no-new-privileges`, `network_mode:
none`).

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
