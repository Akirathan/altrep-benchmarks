
benchmark_func_args <- BASELINE_DATA

benchmark_func <- function(data) {
    .Call("bench_dataptr_inside", PACKAGE="altrepbench", data, ITERATIONS)
    return (TRUE)
}