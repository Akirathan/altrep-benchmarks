
instance <- simple_vec_wrapper.create_instance(BASELINE_DATA)

benchmark_func_args <- instance

benchmark_func <- function(instance_param) {
    .Call("bench_iter_by_region", PACKAGE="altrepbench", instance_param, ITERATIONS)
    return (TRUE)
}