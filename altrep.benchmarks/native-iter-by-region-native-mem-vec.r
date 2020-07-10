
instance <- native_mem_vec.create_instance(LEN)

benchmark_func_args <- instance

benchmark_func <- function(instance_param) {
    .Call("bench_iter_by_region", PACKAGE="altrepbench", instance_param, ITERATIONS)
    return (TRUE)
}