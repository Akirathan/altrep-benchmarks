#include "native_mem_vec.h"
#include <R_ext/Altrep.h>

static int * native_mem_ptr = NULL;
static R_xlen_t data_length = 0;

static void * dataptr_method(SEXP instance, Rboolean writeabble);
static R_xlen_t length_method(SEXP instance);
static int elt_method(SEXP instance, R_xlen_t idx);

SEXP native_mem_vec_create_instance(SEXP data_len)
{
    if (TYPEOF(data_len) != INTSXP) {
        Rf_error("data_len parameter should be integer");
    }

    R_altrep_class_t descr = R_make_altinteger_class("native_mem_vec", "altrepbench", NULL);
    R_set_altrep_Length_method(descr, &length_method);
    R_set_altvec_Dataptr_method(descr, &dataptr_method);
    R_set_altinteger_Elt_method(descr, &elt_method);

    data_length = INTEGER_ELT(data_len, 0);
    native_mem_ptr = malloc(data_length * sizeof(int));
    //SEXP external_ptr = R_MakeExternalPtr(native_mem_ptr, R_NilValue, R_NilValue);
    return R_new_altrep(descr, R_NilValue, R_NilValue);
}

SEXP native_mem_vec_delete_instance()
{
    free(native_mem_ptr);
    return R_NilValue;
}

static void * dataptr_method(SEXP instance, Rboolean writeabble)
{
    // Simulate access to data
    //SEXP data1 = R_altrep_data1(instance);
    return native_mem_ptr;
}

static R_xlen_t length_method(SEXP instance)
{
    return data_length;
}

static int elt_method(SEXP instance, R_xlen_t idx)
{
    // Simulate access to data
    //SEXP data1 = R_altrep_data1(instance);
    return ((int *)native_mem_ptr)[idx];
}
