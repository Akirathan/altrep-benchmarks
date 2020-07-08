/*
 * Copyright (c) 2015, 2020, Oracle and/or its affiliates. All rights reserved.
 * DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
 *
 * This code is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License version 3 only, as
 * published by the Free Software Foundation.
 *
 * This code is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * version 3 for more details (a copy is included in the LICENSE file that
 * accompanied this code).
 *
 * You should have received a copy of the GNU General Public License version
 * 3 along with this work; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * Please contact Oracle, 500 Oracle Parkway, Redwood Shores, CA 94065 USA
 * or visit www.oracle.com if you need additional information or have any
 * questions.
 */
#include <R.h>
#include <Rinternals.h>
#include <R_ext/Rdynload.h>
#include <R_ext/Itermacros.h>
#include "native_mem_vec.h"
#include "generator_altvec.h"

static SEXP bench_dataptr_before(SEXP instance, SEXP iterations);
static SEXP bench_dataptr_inside(SEXP instance, SEXP iterations);
static SEXP bench_iter_by_region(SEXP instance, SEXP iterations);
static SEXP bench_test(SEXP instance);

static const R_CallMethodDef CallEntries[]  = {
    {"bench_dataptr_before", (DL_FUNC) &bench_dataptr_before, 2},
    {"bench_dataptr_inside", (DL_FUNC) &bench_dataptr_inside, 2},
    {"bench_iter_by_region", (DL_FUNC) &bench_iter_by_region, 2},
    {"bench_test", (DL_FUNC) &bench_test, 1},
    {"native_mem_vec_create_instance", (DL_FUNC) &native_mem_vec_create_instance, 1},
    {"native_mem_vec_delete_instance", (DL_FUNC) &native_mem_vec_delete_instance, 0},
    {"generator_altvec_new", (DL_FUNC) &generator_altvec_new, 3},
    {NULL, NULL, 0}
};

void R_init_altrepbench(DllInfo *dll)
{
    R_registerRoutines(dll, NULL, CallEntries, NULL, NULL);
}

/**
 * DATAPTR is invoked before for-cycle.
 */
static SEXP bench_dataptr_before(SEXP instance, SEXP iterations)
{
    if (TYPEOF(instance) != INTSXP || TYPEOF(iterations) != INTSXP) {
        error("Expecting INTSXP type of instance and iterations parameters");
    }
    int iters = INTEGER_ELT(iterations, 0);
    
    int acc = 0;
    int *dataptr = INTEGER(instance);
    for (int i = 0; i < iters; i++) {
        for (int j = 0; j < LENGTH(instance) - 1; j++) {
            acc += *dataptr - *(dataptr + 1);
        }
    }
    return ScalarInteger(acc);
}

// TODO: Pridat jeste neco co skutecne vola dataptr inside

// TODO: Dava smysl spustit to s nasi sekvenci a porovnat to s GNU-R sekvenci.
/**
 * DATAPTR is invoked inside for-cycle.
 */
static SEXP bench_dataptr_inside(SEXP instance, SEXP iterations)
{
    if (TYPEOF(instance) != INTSXP || TYPEOF(iterations) != INTSXP) {
        error("Expecting INTSXP type of instance and iterations parameters");
    }
    int iters = INTEGER_ELT(iterations, 0);

    int acc = 0;
    for (int i = 0; i < iters; i++) {
        for (int j = 0; j < LENGTH(instance) - 1; j++) {
            acc += INTEGER_ELT(instance, j) - INTEGER_ELT(instance, j + 1);
        }
    }
    return ScalarInteger(acc);
}

/**
 * Uses ITERATE_BY_REGION which in turn uses INTEGER_GET_REGION.
 */
static SEXP bench_iter_by_region(SEXP instance, SEXP iterations)
{
    if (TYPEOF(instance) != INTSXP || TYPEOF(iterations) != INTSXP) {
        error("Expecting INTSXP type of instance and iterations parameters");
    }
    int iters = INTEGER_ELT(iterations, 0);

    int acc = 0;
    for (int iter = 0; iter < iters; iter++) {
        ITERATE_BY_REGION(instance, dataptr, outer_idx, nbatch, int, INTEGER, {
            for (R_xlen_t k = 0; k < nbatch - 1; k++) {
                acc += dataptr[k] - dataptr[k + 1];
            }
        });
    }
    return ScalarInteger(acc);
}

static SEXP bench_test(SEXP instance)
{
    int *dataptr = INTEGER(instance);
    int acc = 0;
    for (int i = 0; i < LENGTH(instance); i++) {
        acc += dataptr[i];
    }
    return ScalarInteger(acc);
}