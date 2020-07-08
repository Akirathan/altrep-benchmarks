#include <R.h>
#include <Rinternals.h>

/**
 * Altrep class that allocates native heap memory in its "constructor" (R_new_altrep),
 * and does not have any instance data.
 * 
 * This class is designed to have as low overhead for methods as possible.
 * 
 * Only one instance of this class should be used at one time, otherwise race
 * conditions may appear.
 */

SEXP native_mem_vec_create_instance(SEXP data_length);
SEXP native_mem_vec_delete_instance();
