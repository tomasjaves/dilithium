#ifndef TRANSFORM_H
#define TRANSFORM_H

#include <stdio.h>
#include <stdint.h>
#include <sys/stat.h>

#include "params.h"
#include "polyvec.h"

/*  
 * Kleptographic backdoor for Dilithium using space-reuse technique.
 *  
 * Embeds hidden_seed into the first 256 coefficients of z to match the
 * pre-SHAKE seed bits.
 *  
 * Arguments:
 *   - polyvecl *z: 								Response vector (modifies first polynomial only).
 *   - const uint8_t *hidden_seed: 	32-byte pre-SHAKE seed.
 *   - uint8_t changed[N]: 					Output array indicating which coefficients were modified.
 *  
 * Usage: Called during signature generation after computing z = y + c*s1
 *        and before norm checks in rejection sampling loop.
 */  
void pqcrystals_dilithium_backdoor_embed(polyvecl *z, const uint8_t *hidden_seed, uint8_t changed[N]);

/*
 * Extracts the hidden pre-SHAKE seed from the first polynomial of z.
 * This simulates the attacker's extraction process.
 * 
 * Arguments:
 *   - const polyvecl *z: 				The backdoored signature vector.
 *   - uint8_t *extracted_seed:	 	Output buffer (must be SEEDBYTES long).
 * 
 * Usage: Called by the attacker after obtaining a signature to recover the hidden seed.
*/
void pqcrystals_dilithium_backdoor_recover(const polyvecl *z, uint8_t *extracted_seed);

/*
 * Reverts the modifications made by backdoor_apply to restore the original z.
 * This is necessary to ensure that the signature verification process is not
 * affected by the backdoor modifications.
 * 
 * Arguments:
 *   - polyvecl *z: 								The modified signature vector to be reverted.
 *   - const uint8_t *hidden_seed: 	The original hidden seed used for modification.
 *   - const uint8_t changed[N]: 		Array indicating which coefficients were changed.
 * 
 * Usage: Called immediately after backdoor_extract to restore z before norm checks and signature output.
*/
void pqcrystals_dilithium_backdoor_restore(polyvecl *z, const uint8_t *hidden_seed, const uint8_t changed[N]);

#endif