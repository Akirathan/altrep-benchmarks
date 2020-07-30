
instance <- native_mem_vec.create_instance(LEN)
# TODO: We should call native_mem_vec.delete_instance() after benchmark

benchmark_func_args <- instance

benchmark_func <- function(instance) {
    acc <- 0L
    len <- length(instance)
    for (i in 1:(len - 1L)) {
        acc <- acc + instance[[i]] - instance[[i+1L]]
    }
    return (is.integer(acc))
}
