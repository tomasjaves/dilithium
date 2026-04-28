/*
 * Per-iteration micro-benchmark for Dilithium (FIPS 204).
 *
 * Compiled six times per implementation:
 *   - Mode in {2, 3, 5}
 *   - Backdoor in {on, off}, via -DDILITHIUM_DISABLE_BACKDOOR
 *
 * Always pass -DDILITHIUM_SILENT_BACKDOOR to suppress status.c prints.
 *
 * Output: one CSV per phase plus a summary, written into argv[1].
 *   keygen.csv, sign.csv, verify.csv  (columns: iter,cycles,time_ns,peak_rss_kb,ok)
 *   summary.csv                       (key,value pairs: sizes, pass/fail counts, wall time)
 *
 * Build flags also rely on -I.. so that "sign.h", "params.h" and "randombytes.h"
 * resolve against the implementation directory (ref/ or avx2/).
 */

#define _POSIX_C_SOURCE 200809L
#include <time.h>
#include <sys/resource.h>
#include <sys/stat.h>
#define DEVNULL_PATH "/dev/null"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#include "sign.h"
#include "randombytes.h"

#ifndef NTESTS
#define NTESTS 10000
#endif

#define MLEN   59
#define CTXLEN 14

/* TSC: inline asm on x86-64,
 * fallback to monotonic clock otherwise. */
static inline uint64_t rdtsc_cycles(void) {
#if defined(__x86_64__) || defined(__amd64__)
    uint32_t lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
#endif
}

/* Wall-clock in nanoseconds, monotonic. */
static inline uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

/* Peak resident-set size (KB). */
static long peak_rss_kb(void) {
    struct rusage ru;
    if (getrusage(RUSAGE_SELF, &ru) != 0) return -1;
#ifdef __APPLE__
    return (long)(ru.ru_maxrss / 1024);
#else
    return ru.ru_maxrss;
#endif
}

static int mkdir_p(const char *path) {
    int r = mkdir(path, 0755);
    if (r == 0 || errno == EEXIST) return 0;
    return r;
}

static FILE* open_csv(const char *outdir, const char *name) {
    char path[1024];
    snprintf(path, sizeof(path), "%s/%s", outdir, name);
    FILE *f = fopen(path, "w");
    if (!f) {
        fprintf(stderr, "fopen(%s): %s\n", path, strerror(errno));
        exit(1);
    }
    fprintf(f, "iter,cycles,time_ns,peak_rss_kb,ok\n");
    return f;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <output_dir>\n", argv[0]);
        return 2;
    }
    const char *outdir = argv[1];
    mkdir_p(outdir);

    if (freopen(DEVNULL_PATH, "w", stdout) == NULL) {
        fprintf(stderr, "freopen(%s): %s\n", DEVNULL_PATH, strerror(errno));
        return 1;
    }

    FILE *fkg = open_csv(outdir, "keygen.csv");
    FILE *fsg = open_csv(outdir, "sign.csv");
    FILE *fvf = open_csv(outdir, "verify.csv");

    uint8_t pk[CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[CRYPTO_SECRETKEYBYTES];
    uint8_t sig[CRYPTO_BYTES];
    uint8_t m[MLEN];
    uint8_t ctx[CTXLEN] = {0};
    snprintf((char*)ctx, CTXLEN, "bndlth");
    size_t siglen;

    int kg_ok = 0, kg_fail = 0;
    int sg_ok = 0, sg_fail = 0;
    int vf_ok = 0, vf_fail = 0;

    uint64_t bench_start = now_ns();

    for (int i = 0; i < NTESTS; i++) {
        randombytes(m, MLEN);

        /* KEYGEN */
        uint64_t t0 = now_ns();
        uint64_t c0 = rdtsc_cycles();
        int r = crypto_sign_keypair(pk, sk);
        uint64_t c1 = rdtsc_cycles();
        uint64_t t1 = now_ns();
        int ok = (r == 0);
        if (ok) kg_ok++; else kg_fail++;
        fprintf(fkg, "%d,%llu,%llu,%ld,%d\n",
                i,
                (unsigned long long)(c1 - c0),
                (unsigned long long)(t1 - t0),
                peak_rss_kb(), ok);

        /* SIGN */
        t0 = now_ns();
        c0 = rdtsc_cycles();
        r = crypto_sign_signature(sig, &siglen, m, MLEN, ctx, CTXLEN, sk);
        c1 = rdtsc_cycles();
        t1 = now_ns();
        ok = (r == 0);
        if (ok) sg_ok++; else sg_fail++;
        fprintf(fsg, "%d,%llu,%llu,%ld,%d\n",
                i,
                (unsigned long long)(c1 - c0),
                (unsigned long long)(t1 - t0),
                peak_rss_kb(), ok);

        /* VERIFY */
        t0 = now_ns();
        c0 = rdtsc_cycles();
        r = crypto_sign_verify(sig, siglen, m, MLEN, ctx, CTXLEN, pk);
        c1 = rdtsc_cycles();
        t1 = now_ns();
        ok = (r == 0);
        if (ok) vf_ok++; else vf_fail++;
        fprintf(fvf, "%d,%llu,%llu,%ld,%d\n",
                i,
                (unsigned long long)(c1 - c0),
                (unsigned long long)(t1 - t0),
                peak_rss_kb(), ok);

        if ((i + 1) % 1000 == 0) {
            fprintf(stderr, "[%s] %d / %d\n", argv[0], i + 1, NTESTS);
        }
    }

    uint64_t bench_end = now_ns();

    fclose(fkg);
    fclose(fsg);
    fclose(fvf);

    char path[1024];
    snprintf(path, sizeof(path), "%s/summary.csv", outdir);
    FILE *fs = fopen(path, "w");
    if (!fs) {
        fprintf(stderr, "fopen(%s): %s\n", path, strerror(errno));
        return 1;
    }
    fprintf(fs, "metric,value\n");
    fprintf(fs, "alg,%s\n", CRYPTO_ALGNAME);
#ifdef DILITHIUM_ENABLE_BACKDOOR
    fprintf(fs, "backdoor,1\n");
#else
    fprintf(fs, "backdoor,0\n");
#endif
    fprintf(fs, "ntests,%d\n", NTESTS);
    fprintf(fs, "pk_bytes,%d\n", CRYPTO_PUBLICKEYBYTES);
    fprintf(fs, "sk_bytes,%d\n", CRYPTO_SECRETKEYBYTES);
    fprintf(fs, "sig_bytes,%d\n", CRYPTO_BYTES);
    fprintf(fs, "keygen_ok,%d\n", kg_ok);
    fprintf(fs, "keygen_fail,%d\n", kg_fail);
    fprintf(fs, "sign_ok,%d\n", sg_ok);
    fprintf(fs, "sign_fail,%d\n", sg_fail);
    fprintf(fs, "verify_ok,%d\n", vf_ok);
    fprintf(fs, "verify_fail,%d\n", vf_fail);
    fprintf(fs, "peak_rss_kb,%ld\n", peak_rss_kb());
    fprintf(fs, "wall_time_ns,%llu\n",
            (unsigned long long)(bench_end - bench_start));
    fclose(fs);

    fprintf(stderr, "[%s] done -> %s\n", argv[0], outdir);
    return 0;
}
