LEN <- as.integer(10)
data <- as.integer(runif(LEN, min=1, max=100))

benchmark_func_args <- data

benchmark_func <- function(instance_param) {
    Sys.sleep(0.2)
    return (TRUE)
}
