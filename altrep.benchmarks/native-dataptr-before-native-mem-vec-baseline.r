
benchmark_func_args <- BASELINE_DATA

benchmark_func <- function(data) {
    .Call("bench_dataptr_before", PACKAGE="altrepbench", data, ITERATIONS)
    return (TRUE)
}