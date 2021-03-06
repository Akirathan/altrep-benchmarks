
benchmark_func_args <- BASELINE_DATA

benchmark_func <- function(data) {
    acc <- 0L
    len <- length(data)
    for (i in 1:(len - 1L)) {
        acc <- acc + data[[i]] - data[[i+1L]]
    }
    return (is.integer(acc))
}