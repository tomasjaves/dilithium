# Supplementary material of the extended abstract

Data and programs generated after the defense of the thesis for the extended
abstract *Practical Implementation of a Backdoor Attack on ML-DSA
(CRYSTALS-Dilithium)* ("Tengo un Proyecto" award, 9th edition, 2026). They use
the code of tag `tfg-2026` (the defended version) without changes: `ref/` and
`hypothesis_tests/` are identical in that tag and in this commit.

All commands run from the root of the repository. Keys and messages come from
the system random number generator, so a new run produces other keys and
counts of the same order.

## `fig2/`: Fig. 2 of the extended abstract

`z_D2_nobd.csv` and `z_D2_bd.csv` hold the first polynomial of `z` of 50
signatures of one key each, written by `hypothesis_tests/dump_z.c` for the
reference ML-DSA-44 without and with the backdoor. They were built with the
flags of the `dump` target of `ref/Makefile` (gcc 13.3.0) plus
`-DNUM_KEYPAIRS=1`, so that each dump contains one key:

```
cd ref && mkdir -p dump
FLAGS="-Wall -Wextra -Wpedantic -Wmissing-prototypes -Wredundant-decls -Wshadow -Wvla \
  -Wpointer-arith -O3 -fomit-frame-pointer -I. -DDILITHIUM_SILENT_BACKDOOR \
  -DDILITHIUM_MODE=2 -DNUM_KEYPAIRS=1"
SRC="../hypothesis_tests/dump_z.c randombytes.c sign.c transform.c status.c packing.c \
  polyvec.c poly.c ntt.c reduce.c rounding.c fips202.c symmetric-shake.c"
cc $FLAGS -o dump/dump2_bd $SRC && ./dump/dump2_bd
cc $FLAGS -DDILITHIUM_DISABLE_BACKDOOR -o dump/dump2_nobd $SRC && ./dump/dump2_nobd
cd ..
```

The unmodified build signs in the default hedged mode and the backdoored build
in deterministic mode, as in the thesis.

Statistical tests of the thesis on these dumps:

```
python3 hypothesis_tests/hypothesis_tests.py \
  --original extended_abstract/fig2/z_D2_nobd.csv \
  --backdoor extended_abstract/fig2/z_D2_bd.csv
```

Result: the legitimate key has an aggregate chi-squared statistic of 271.7
(critical value 294.3), a mean variance of 0.2497, and no significant position;
the backdoored key has 12 800, a mean variance of 0, and all 256 positions
constant.

Figure (needs numpy, pandas, matplotlib, and pdflatex):

```
cd extended_abstract/fig2
python3 make_fig2.py z_D2_nobd.csv z_D2_bd.csv lsb_fractions.pdf
```

## `norm_bound/`: norm bound of the restored response (Section IV-C)

`edge_check.c` generates backdoored signatures with the reference code, each
with a fresh key pair and message, restores them as the compromised verifier
does, and counts the restored responses that violate
`||z||_inf < GAMMA1 - BETA`. Build and run for `M` = 2, 3, or 5 (ML-DSA-44,
ML-DSA-65, ML-DSA-87):

```
R=ref; M=2
cc -O3 -DDILITHIUM_MODE=$M -DDILITHIUM_SILENT_BACKDOOR -I$R -o edge$M \
  extended_abstract/norm_bound/edge_check.c $R/randombytes.c $R/sign.c \
  $R/transform.c $R/status.c $R/packing.c $R/polyvec.c $R/poly.c $R/ntt.c \
  $R/reduce.c $R/rounding.c $R/fips202.c $R/symmetric-shake.c
./edge$M 100000
```

`results.txt` holds the output of the runs reported in the article: 51, 17,
and 10 cases in 100 000 signatures per parameter set (expected about 48.8,
12.2, and 12.2), all accepted by the compromised verifier.
