
instance <- native_mem_vec.create_instance(LEN)
benchmark_func_args <- instance

benchmark_func <- function(instance) {
    .Call("bench_dataptr_before", PACKAGE="altrepbench", instance, ITERATIONS)
    return (TRUE)
}
