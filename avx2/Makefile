CC ?= /usr/bin/cc
CFLAGS += -Wall -Wextra -Wpedantic -Wmissing-prototypes -Wredundant-decls \
  -Wshadow -Wpointer-arith -mavx2 -mpopcnt \
  -march=native -mtune=native -O3
NISTFLAGS += -Wno-unused-result -mavx2 -mpopcnt \
  -march=native -mtune=native -O3
SOURCES = sign.c transform.c status.c packing.c polyvec.c poly.c ntt.S invntt.S pointwise.S \
  shuffle.S consts.c rejsample.c rounding.c
HEADERS = align.h config.h params.h api.h sign.h packing.h polyvec.h poly.h ntt.h \
  consts.h shuffle.inc rejsample.h rounding.h symmetric.h randombytes.h transform.h status.h
KECCAK_SOURCES = $(SOURCES) fips202.c fips202x4.c f1600x4.S symmetric-shake.c
KECCAK_HEADERS = $(HEADERS) fips202.h fips202x4.h

.PHONY: all shared bench bench-clean clean

all: \
  test/test_dilithium2 \
  test/test_dilithium3 \
  test/test_dilithium5 \
  test/test_vectors2 \
  test/test_vectors3 \
  test/test_vectors5 \
  speed

speed: \
  test/test_speed2 \
  test/test_speed3 \
  test/test_speed5 \

BENCH_BD   = bench/bench2_bd   bench/bench3_bd   bench/bench5_bd
BENCH_NOBD = bench/bench2_nobd bench/bench3_nobd bench/bench5_nobd
BENCH_DEPS = ../benchmarks/bench.c randombytes.c $(KECCAK_SOURCES) $(KECCAK_HEADERS)

bench: $(BENCH_BD) $(BENCH_NOBD)

shared: \
  libpqcrystals_dilithium2_avx2.so \
  libpqcrystals_dilithium3_avx2.so \
  libpqcrystals_dilithium5_avx2.so \
  libpqcrystals_fips202_avx2.so \
  libpqcrystals_fips202x4_avx2.so \

libpqcrystals_fips202_avx2.so: fips202.c fips202.h
	$(CC) -shared -fPIC $(CFLAGS) -o $@ $<

libpqcrystals_fips202x4_avx2.so: fips202x4.c fips202x4.h f1600x4.S
	$(CC) -shared -fPIC $(CFLAGS) -o $@ $< f1600x4.S

libpqcrystals_dilithium2_avx2.so: $(SOURCES) $(HEADERS) symmetric-shake.c
	$(CC) -shared -fPIC $(CFLAGS) -DDILITHIUM_MODE=2 \
	  -o $@ $(SOURCES) symmetric-shake.c

libpqcrystals_dilithium3_avx2.so: $(SOURCES) $(HEADERS) symmetric-shake.c
	$(CC) -shared -fPIC $(CFLAGS) -DDILITHIUM_MODE=3 \
	  -o $@ $(SOURCES) symmetric-shake.c

libpqcrystals_dilithium5_avx2.so: $(SOURCES) $(HEADERS) symmetric-shake.c
	$(CC) -shared -fPIC $(CFLAGS) -DDILITHIUM_MODE=5 \
	  -o $@ $(SOURCES) symmetric-shake.c

test/test_dilithium2: test/test_dilithium.c randombytes.c $(KECCAK_SOURCES) \
  $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=2 \
	  -o $@ $< randombytes.c $(KECCAK_SOURCES)

test/test_dilithium3: test/test_dilithium.c randombytes.c $(KECCAK_SOURCES) \
  $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=3 \
	  -o $@ $< randombytes.c $(KECCAK_SOURCES)

test/test_dilithium5: test/test_dilithium.c randombytes.c $(KECCAK_SOURCES) \
  $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=5 \
	  -o $@ $< randombytes.c $(KECCAK_SOURCES)

test/test_vectors2: test/test_vectors.c $(KECCAK_SOURCES) $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=2 \
	  -o $@ $< $(KECCAK_SOURCES)

test/test_vectors3: test/test_vectors.c $(KECCAK_SOURCES) $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=3 \
	  -o $@ $< $(KECCAK_SOURCES)

test/test_vectors5: test/test_vectors.c $(KECCAK_SOURCES) $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=5 \
	  -o $@ $< $(KECCAK_SOURCES)

test/test_speed2: test/test_speed.c test/speed_print.c test/speed_print.h \
  test/cpucycles.c test/cpucycles.h randombytes.c $(KECCAK_SOURCES) \
  $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=2 \
	  -o $@ $< test/speed_print.c test/cpucycles.c randombytes.c \
	  $(KECCAK_SOURCES)

test/test_speed3: test/test_speed.c test/speed_print.c test/speed_print.h \
  test/cpucycles.c test/cpucycles.h randombytes.c $(KECCAK_SOURCES) \
  $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=3 \
	  -o $@ $< test/speed_print.c test/cpucycles.c randombytes.c \
	  $(KECCAK_SOURCES)

test/test_speed5: test/test_speed.c test/speed_print.c test/speed_print.h \
  test/cpucycles.c test/cpucycles.h randombytes.c $(KECCAK_SOURCES) \
  $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -DDILITHIUM_MODE=5 \
	  -o $@ $< test/speed_print.c test/cpucycles.c randombytes.c \
	  $(KECCAK_SOURCES)

test/test_mul: test/test_mul.c randombytes.c $(KECCAK_SOURCES) \
  $(KECCAK_HEADERS)
	$(CC) $(CFLAGS) -UDBENCH -o $@ $< randombytes.c $(KECCAK_SOURCES)

# --- Benchmark binaries (TFG: con/sin puerta trasera) ---------------------
# Static pattern rules: explicit target lists eliminate any pattern ambiguity
# between *_bd and *_nobd suffixes.
#   _bd:    backdoor enabled (default config.h)
#   _nobd:  backdoor disabled via -DDILITHIUM_DISABLE_BACKDOOR
# Both pass -DDILITHIUM_SILENT_BACKDOOR to suppress status.c prints.


# --- dump_z binaries (hypothesis tests: multiple sigs per keypair) --------
DUMP_BD   = dump/dump2_bd   dump/dump3_bd   dump/dump5_bd
DUMP_NOBD = dump/dump2_nobd dump/dump3_nobd dump/dump5_nobd
DUMP_DEPS = ../benchmarks/dump_z.c randombytes.c $(KECCAK_SOURCES) $(KECCAK_HEADERS)

dump: $(DUMP_BD) $(DUMP_NOBD)

$(DUMP_BD): dump/dump%_bd: $(DUMP_DEPS)
	@mkdir -p -- dump
	$(CC) $(CFLAGS) -I. -DDILITHIUM_SILENT_BACKDOOR -DDILITHIUM_MODE=$* \
	  -o $@ $< randombytes.c $(KECCAK_SOURCES)

$(DUMP_NOBD): dump/dump%_nobd: $(DUMP_DEPS)
	@mkdir -p -- dump
	$(CC) $(CFLAGS) -I. -DDILITHIUM_SILENT_BACKDOOR -DDILITHIUM_DISABLE_BACKDOOR -DDILITHIUM_MODE=$* \
	  -o $@ $< randombytes.c $(KECCAK_SOURCES)

dump-clean:
	rm -rf dump
# --- end dump_z binaries --------------------------------------------------

clean: bench-clean dump-clean
	rm -f *.o *.a *.so
	rm -rf output
	rm -f test/test_dilithium2
	rm -f test/test_dilithium3
	rm -f test/test_dilithium5
	rm -f test/test_vectors2
	rm -f test/test_vectors3
	rm -f test/test_vectors5
	rm -f test/test_speed2
	rm -f test/test_speed3
	rm -f test/test_speed5
	rm -f test/test_mul
