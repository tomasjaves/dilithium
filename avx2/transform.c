#include "transform.h"

void pqcrystals_dilithium_backdoor_embed(polyvecl *z, const uint8_t *hidden_seed, uint8_t changed[N]) {
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

void pqcrystals_dilithium_backdoor_recover(const polyvecl *z, uint8_t *extracted_seed) {
	for(unsigned int i = 0; i < SEEDBYTES; ++i) {
		extracted_seed[i] = 0;
		for(unsigned int j = 0; j < 8; ++j) {
			uint8_t bit = (uint8_t)(((uint32_t)z->vec[0].coeffs[i * 8 + j]) & 1u);
			extracted_seed[i] |= (bit << j);
		}
	}
}

void pqcrystals_dilithium_backdoor_restore(polyvecl *z, const uint8_t *hidden_seed, const uint8_t changed[N]) {
	for(unsigned int i = 0; i < N; ++i) {
		if(changed[i]) {
			uint8_t seed_i = (hidden_seed[i >> 3] >> (i & 7)) & 1u;
			z->vec[0].coeffs[i] += seed_i == 0 ? -1 : 1;
		}
	}
	poly_reduce(&z->vec[0]);
}
