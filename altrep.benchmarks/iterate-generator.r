generator_func <- function(idx) {
    as.integer(idx + 1)
}
fn <- as.symbol("generator_func")
instance <- generator_altvec.new(LEN, fn)

benchmark_func_args <- instance

benchmark_func <- function(instance) {
    acc <- 0L
    len <- length(instance)
    for (i in 1:(len - 1L)) {
        acc <- acc + instance[[i]] - instance[[i+1L]]
    }
    return (is.integer(acc))
}