
instance <- simple_vec_wrapper.create_instance(BASELINE_DATA, gen.Elt=TRUE)

benchmark_func_args <- instance

benchmark_func <- function(instance_param) {
    .Call("bench_dataptr_inside", PACKAGE="altrepbench", instance_param, ITERATIONS)
    return (TRUE)
}