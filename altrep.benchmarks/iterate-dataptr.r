
instance <- simple_vec_wrapper.create_instance(BASELINE_DATA)

benchmark_func_args <- instance

benchmark_func <- function(instance) {
    acc <- 0L
    len <- length(instance)
    for (i in 1:(len - 1L)) {
        # Subscript should use Dataptr at some point.
        acc <- acc + instance[[i]] - instance[[i+1L]]
    }
    return (is.integer(acc))
}