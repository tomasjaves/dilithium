#include "backdoor.h"

void backdoor_apply(polyvecl *z, const uint8_t *hidden_seed, uint8_t changed[N]) {
	for(unsigned int i = 0; i < N; ++i) {
		uint8_t seed_i = (hidden_seed[i >> 3] >> (i & 7)) & 1u;
		uint8_t zi_mod2 = (uint8_t)(((uint32_t)z->vec[0].coeffs[i]) & 1u);

		if(zi_mod2 != seed_i) {
			z->vec[0].coeffs[i] += seed_i == 0 ? 1 : -1;
			changed[i] = 1;
		} else changed[i] = 0;
	}
	poly_reduce(&z->vec[0]);
}

void backdoor_extract(const polyvecl *z, uint8_t *extracted_seed) {
	for(unsigned int i = 0; i < SEEDBYTES; ++i) {
		extracted_seed[i] = 0;
		for(unsigned int j = 0; j < 8; ++j) {
			uint8_t bit = (uint8_t)(((uint32_t)z->vec[0].coeffs[i * 8 + j]) & 1u);
			extracted_seed[i] |= (bit << j);
		}
	}
}

void backdoor_revert(polyvecl *z, const uint8_t *hidden_seed, const uint8_t changed[N]) {
	for(unsigned int i = 0; i < N; ++i) {
		if(changed[i]) {
			uint8_t seed_i = (hidden_seed[i >> 3] >> (i & 7)) & 1u;
			z->vec[0].coeffs[i] += seed_i == 0 ? -1 : 1;
		}
	}
	poly_reduce(&z->vec[0]);
}

void hidden_seed_prove(const char* context, const uint8_t *hidden_seed) {
	printf("\n[%s] Value of seed:\n", context);
	for(unsigned int i = 0; i < SEEDBYTES; ++i) {
		printf("%02x", hidden_seed[i]);
		printf(i % 16 == 15 ? "\n" : " ");
	}
}

void key_prove(const char* context, const uint8_t *key) {
	printf("\n[%s] Value of key: ", context);
	for(unsigned int i = 0; i < SEEDBYTES; ++i) {
		printf("%02x", key[i]);
	}
	printf("\n");
}

void first_256_coefficients_prove(const polyvecl *z) {
	for(unsigned int i = 0; i < 8; ++i) {
		printf("%d ", z->vec[0].coeffs[i]);
	}
	printf("\n");
}
