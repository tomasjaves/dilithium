/* Counts backdoored signatures whose restored z violates ||z||_inf < GAMMA1-BETA.
 * Uses the reference code of tag tfg-2026 (ref/config.h enables the backdoor by
 * default); see extended_abstract/README.md for the build command. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "params.h"
#include "api.h"
#include "sign.h"
#include "packing.h"
#include "polyvec.h"
#include "poly.h"
#include "fips202.h"
#include "randombytes.h"
#include "transform.h"

int main(int argc, char **argv) {
  long n = argc > 1 ? atol(argv[1]) : 1000;
  uint8_t pk[CRYPTO_PUBLICKEYBYTES], sk[CRYPTO_SECRETKEYBYTES], sig[CRYPTO_BYTES];
  uint8_t m[32], c[CTILDEBYTES], seed[SEEDBYTES], tr[TRBYTES], mu[CRHBYTES];
  uint8_t pre[2] = {0, 0};
  size_t siglen;
  polyvecl z; polyveck h; poly cp;
  keccak_state st;
  long accepted = 0, restored = 0, violating = 0, viol_coeffs = 0, odd_cases = 0;
  for (long t = 0; t < n; t++) {
    crypto_sign_keypair(pk, sk);
    randombytes(m, sizeof m);
    crypto_sign_signature(sig, &siglen, m, sizeof m, NULL, 0, sk);
    if (crypto_sign_verify(sig, siglen, m, sizeof m, NULL, 0, pk) == 0) accepted++;
    /* restore as the compromised verifier does */
    if (unpack_sig(c, &z, &h, sig)) continue;
    shake256(tr, TRBYTES, pk, CRYPTO_PUBLICKEYBYTES);
    shake256_init(&st);
    shake256_absorb(&st, tr, TRBYTES);
    shake256_absorb(&st, pre, 2);
    shake256_absorb(&st, m, sizeof m);
    shake256_finalize(&st);
    shake256_squeeze(mu, CRHBYTES, &st);
    poly_challenge(&cp, c);
    pqcrystals_dilithium_backdoor_recover(&z, seed);
    if (pqcrystals_dilithium_backdoor_restore(&z, seed, mu, &cp) != 0) continue;
    restored++;
    if (polyvecl_chknorm(&z, GAMMA1 - BETA)) {
      violating++;
      for (int i = 0; i < N; i++) {
        int32_t v = z.vec[0].coeffs[i];
        int bit = (seed[i >> 3] >> (i & 7)) & 1;
        if (v >= GAMMA1 - BETA || v <= -(GAMMA1 - BETA)) {
          viol_coeffs++;
          if (!(v == GAMMA1 - BETA && bit == 1)) odd_cases++;
        }
      }
      for (unsigned k = 1; k < L; k++)
        if (poly_chknorm(&z.vec[k], GAMMA1 - BETA)) odd_cases++;
    }
  }
  printf("mode=%d n=%ld accepted=%ld restored=%ld violating=%ld coeffs=%ld other=%ld expected=%.2f\n",
         DILITHIUM_MODE, n, accepted, restored, violating, viol_coeffs, odd_cases, n * 64.0 / GAMMA1);
  return 0;
}
