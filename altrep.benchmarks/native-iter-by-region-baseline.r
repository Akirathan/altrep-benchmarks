
benchmark_func_args <- BASELINE_DATA

benchmark_func <- function(data) {
    .Call("bench_iter_by_region", PACKAGE="altrepbench", data, ITERATIONS)
    return (TRUE)
}