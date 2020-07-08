
instance <- simple_vec_wrapper.create_instance(BASELINE_DATA, gen.Elt=TRUE)

native_dataptr_bench <- function(instance_param) {
    .Call("bench_dataptr_before", PACKAGE="altrepbench", instance_param, ITERATIONS)
    return (TRUE)
}

baseline_func <- function(...) {
    .Call("bench_dataptr_before", PACKAGE="altrepbench", BASELINE_DATA, ITERATIONS)
    return (TRUE)
}

benchmark(native_dataptr_bench, instance, baseline=baseline_func)