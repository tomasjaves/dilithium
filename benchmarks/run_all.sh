#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS="$SCRIPT_DIR/results"

IMPLS_DEFAULT=("ref" "avx2")
MODES_DEFAULT=("2" "3" "5")
VARIANTS_DEFAULT=("bd" "nobd")

IMPLS=("${IMPLS_DEFAULT[@]}")
MODES=("${MODES_DEFAULT[@]}")
VARIANTS=("${VARIANTS_DEFAULT[@]}")
if [ "$#" -ge 1 ]; then IMPLS=("$1"); fi
if [ "$#" -ge 2 ]; then MODES=("$2"); fi
if [ "$#" -ge 3 ]; then VARIANTS=("$3"); fi

variant_to_folder() {
    case "$1" in
        bd)   echo "with_bd" ;;
        nobd) echo "without_bd" ;;
        *)    echo "Unknown variant: $1" >&2; exit 1 ;;
    esac
}

echo "==> Building bench binaries"
for impl in "${IMPLS[@]}"; do
    echo "    -> $impl"
    mkdir -p "$ROOT/$impl/bench"
    make -C "$ROOT/$impl" bench
done

echo "==> Running benchmarks"
mkdir -p "$RESULTS"
for impl in "${IMPLS[@]}"; do
    for mode in "${MODES[@]}"; do
        for variant in "${VARIANTS[@]}"; do
            folder="$(variant_to_folder "$variant")"
            outdir="$RESULTS/$impl/Dilithium${mode}/${folder}"
            mkdir -p "$outdir"
            bin="$ROOT/$impl/bench/bench${mode}_${variant}"
            if [ ! -x "$bin" ]; then
                echo "Missing binary: $bin" >&2
                exit 1
            fi
            echo "    -> $bin  ->  $outdir"
            "$bin" "$outdir"
        done
    done
done

echo "==> Done. CSVs under $RESULTS"
