#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>

#include "sign.h"
#include "packing.h"
#include "polyvec.h"
#include "poly.h"
#include "randombytes.h"
#include "params.h"

#ifndef NUM_KEYPAIRS
#define NUM_KEYPAIRS 50
#endif

#ifndef SIGS_PER_KEY
#define SIGS_PER_KEY 50
#endif

#define MLEN   59
#define CTXLEN 6

int main(void)
{
    const char *bd_tag;
#ifdef DILITHIUM_ENABLE_BACKDOOR
    bd_tag = "bd";
#else
    bd_tag = "nobd";
#endif

    char outpath[256];
    snprintf(outpath, sizeof(outpath), "dump/z_D%d_%s.csv",
             DILITHIUM_MODE, bd_tag);

    mkdir("dump", 0755);

    FILE *fp = fopen(outpath, "w");
    if (!fp) {
        fprintf(stderr, "fopen(%s): %s\n", outpath, strerror(errno));
        return 1;
    }

    fprintf(fp, "keypair_id,signature_id");
    for (int i = 0; i < N; i++)
        fprintf(fp, ",coeff_%d", i);
    fprintf(fp, "\n");

    uint8_t pk[CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[CRYPTO_SECRETKEYBYTES];
    uint8_t sig[CRYPTO_BYTES];
    uint8_t m[MLEN];
    uint8_t ctx[CTXLEN] = "dumpz";
    size_t  siglen;

    uint8_t  c_tilde[CTILDEBYTES];
    polyvecl z;
    polyveck h;

    for (int kp = 0; kp < NUM_KEYPAIRS; kp++) {
        crypto_sign_keypair(pk, sk);

        for (int s = 0; s < SIGS_PER_KEY; s++) {
            randombytes(m, MLEN);

            crypto_sign_signature(sig, &siglen, m, MLEN, ctx, CTXLEN, sk);

            if (unpack_sig(c_tilde, &z, &h, sig) != 0) {
                fprintf(stderr, "Error unpack_sig kp=%d sig=%d\n", kp, s);
                continue;
            }

            fprintf(fp, "%d,%d", kp, s);
            for (int i = 0; i < N; i++)
                fprintf(fp, ",%d", z.vec[0].coeffs[i]);
            fprintf(fp, "\n");
        }

        if ((kp + 1) % 10 == 0)
            fprintf(stderr, "[D%d-%s] keypairs: %d/%d\n",
                    DILITHIUM_MODE, bd_tag, kp + 1, NUM_KEYPAIRS);
    }

    fclose(fp);
    fprintf(stderr, "Done: %d rows -> %s\n",
            NUM_KEYPAIRS * SIGS_PER_KEY, outpath);
    return 0;
}
