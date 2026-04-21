#ifndef STATUS_H
#define STATUS_H

#include <stdio.h>
#include <stdint.h>
#include <sys/stat.h>
#include "polyvec.h"

/*
 * Prints a labeled 32-byte seed value to stdout.
 * Used for debugging and demonstration purposes to show the hidden seed value.
 *
 * Arguments:
 *   - const char *context:        	Label printed before the hex dump (e.g. "KEYGEN", "EXTRACTED").
 *   - const uint8_t *hidden_seed: 	32-byte buffer to display.
 */
void pqcrystals_dilithium_status_print_seed(const char* context, const uint8_t *hidden_seed);

/*
 * Writes the value of the hidden seed used in the backdoor to the log file.
 * The log includes a context label and a hex dump of the seed.
 *
 * Arguments:
 *   - const char* context:				 Label printed before the hex dump (e.g. "KEYGEN", "SIGN", "EXTRACTED").
 *   - const uint8_t *hidden_seed: 32-byte buffer containing the hidden seed.
 */
void pqcrystals_dilithium_status_log_seed(const char* context, const uint8_t *hidden_seed);

/*
 * Prints a labeled 32-byte key value to stdout.
 * Used to verify that the post-SHAKE key matches between keygen and signing.
 *
 * Arguments:
 *   - const char *context:	 Label printed before the hex dump.
 *   - const uint8_t *key:   32-byte key buffer to display.
 */
void pqcrystals_dilithium_status_print_key(const char* context, const uint8_t *key);

/*
 * Writes the value of the real key derived from the hidden seed to the log file.
 * The log includes a context label and a hex dump of the key.
 *
 * Arguments:
 *   - const char* context:      Label printed before the hex dump.
 *   - const uint8_t *key:       32-byte buffer containing the key.
 */
void pqcrystals_dilithium_status_log_key(const char* context, const uint8_t *key);

#endif
