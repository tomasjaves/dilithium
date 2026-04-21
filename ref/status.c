#include "status.h"

static FILE* open_log(void) {
    mkdir("output", 0755);
    return fopen("output/backdoor_log.txt", "a");
}

void pqcrystals_dilithium_status_print_seed(const char* context, const uint8_t *hidden_seed) {
	printf("\n[%s] Value of seed:\n", context);
	for(unsigned int i = 0; i < SEEDBYTES; ++i) {
		printf("%02x", hidden_seed[i]);
		printf(i % 16 == 15 ? "\n" : " ");
	}
}

void pqcrystals_dilithium_status_log_seed(const char* context, const uint8_t *hidden_seed) {
    FILE *f = open_log();
    if(!f) return;
    fprintf(f, "\n[%s] Value of seed:\n", context);
    for(unsigned int i = 0; i < SEEDBYTES; ++i) {
        fprintf(f, "%02x", hidden_seed[i]);
        fprintf(f, i % 16 == 15 ? "\n" : " ");
    }
    fclose(f);
}

void pqcrystals_dilithium_status_print_key(const char* context, const uint8_t *key) {
	printf("\n[%s] Value of key: ", context);
	for(unsigned int i = 0; i < SEEDBYTES; ++i) {
		printf("%02x", key[i]);
	}
	printf("\n");
}

void pqcrystals_dilithium_status_log_key(const char* context, const uint8_t *key) {
    FILE *f = open_log();
    if(!f) return;
    fprintf(f, "\n[%s] Value of key: ", context);
    for(unsigned int i = 0; i < SEEDBYTES; ++i) {
        fprintf(f, "%02x", key[i]);
    }
    fprintf(f, "\n");
    fclose(f);
}