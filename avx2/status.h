#ifndef STATUS_H
#define STATUS_H

#include <stdio.h>
#include <stdint.h>
#include <sys/stat.h>
#include "polyvec.h"

/*
 * Proves that the hidden seed is correct.
 *
 * Arguments:
 *   - const char* context:        Label printed before the hex dump (e.g. "KEYGEN", "SIGN", "EXTRACTED").
 *   - const uint8_t *hidden_seed: 32-byte buffer containing the hidden seed.
 */
void hidden_seed_prove(const char* context, const uint8_t *hidden_seed);

/*
 * Writes the value of the hidden seed used in the backdoor to the log file.
 * The log includes a context label and a hex dump of the seed.
 *
 * Arguments:
 *   - const char* context:        Label printed before the hex dump (e.g. "KEYGEN", "SIGN", "EXTRACTED").
 *   - const uint8_t *hidden_seed: 32-byte buffer containing the hidden seed.
 */
void log_hidden_seed(const char* context, const uint8_t *hidden_seed);

/*
 * Proves that the key is correct.
 *
 * Arguments:
 *   - const char* context:      Label printed before the hex dump.
 *   - const uint8_t *key:       32-byte buffer containing the key.
 */
void key_prove(const char* context, const uint8_t *key);

/*
 * Writes the value of the real key derived from the hidden seed to the log file.
 * The log includes a context label and a hex dump of the key.
 *
 * Arguments:
 *   - const char* context:      Label printed before the hex dump.
 *   - const uint8_t *key:       32-byte buffer containing the key.
 */
void log_key(const char* context, const uint8_t *key);

#endif
