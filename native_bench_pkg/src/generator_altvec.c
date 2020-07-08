#include "generator_altvec.h"
#include <R_ext/Altrep.h>

static void * dataptr_method(SEXP instance, Rboolean writeabble);
static const void * dataptr_or_null_method(SEXP instance);
static R_xlen_t length_method(SEXP instance);
static int elt_method(SEXP instance, R_xlen_t idx);

// TODO: This should be an instance parameter.
static R_xlen_t data_length = 0;

SEXP generator_altvec_new(SEXP data_length_param, SEXP fn, SEXP rho)
{
    if (TYPEOF(data_length_param) != INTSXP || TYPEOF(fn) != SYMSXP || TYPEOF(rho) != ENVSXP) {
        error("Wrong parameter types");
    }
    data_length = (R_xlen_t) INTEGER_ELT(data_length_param, 0);
    SEXP fcall = lang2(fn, R_NilValue);

    R_altrep_class_t descr = R_make_altinteger_class("GeneratorAltvec", "altrepbench", NULL);
    R_set_altrep_Length_method(descr, &length_method);
    R_set_altvec_Dataptr_or_null_method(descr, &dataptr_or_null_method);
    R_set_altvec_Dataptr_method(descr, &dataptr_method);
    R_set_altinteger_Elt_method(descr, &elt_method);
    return R_new_altrep(descr, fcall, rho);
}

static R_xlen_t length_method(SEXP instance)
{
    return data_length;
}

static void * dataptr_method(SEXP instance, Rboolean writeabble)
{
    // Deliberate violation of Dataptr contract.
    error("This method should not be called");
}

static const void * dataptr_or_null_method(SEXP instance)
{
    // We do not want to materialize, if possible.
    return NULL;
}

static int elt_method(SEXP instance, R_xlen_t idx)
{
    SEXP fcall = R_altrep_data1(instance);
    SEXP rho = R_altrep_data2(instance);
    // Note that there needs to be a conversion from 0-based C index to 1-base R index.
    SETCADR(fcall, ScalarInteger(idx + 1));
    // call f(idx)
    SEXP elt = eval(fcall, rho);
    return INTEGER_ELT(elt, 0);
}
