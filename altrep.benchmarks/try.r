LEN <- as.integer(10)
data <- as.integer(runif(LEN, min=1, max=100))

bench_func <- function(instance_param) {
    Sys.sleep(0.2)
    return (TRUE)
}

baseline_func <- function(param) {
    Sys.sleep(0.2)
    return (TRUE)
}

benchmark(bench_func, data, baseline=baseline_func)
