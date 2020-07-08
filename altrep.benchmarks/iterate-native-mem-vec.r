
instance <- native_mem_vec.create_instance(LEN)

iter_benchmark <- function(instance) {
    acc <- 0L
    len <- length(instance)
    for (i in 1:(len - 1L)) {
        # Subscript should use BASELINE_DATAptr at some point.
        acc <- acc + instance[[i]] - instance[[i+1L]]
    }
    return (is.integer(acc))
}

baseline_func <- function(...) {
    acc <- 0L
    len <- length(BASELINE_DATA)
    for (i in 1:(len - 1L)) {
        acc <- acc + BASELINE_DATA[[i]] - BASELINE_DATA[[i+1L]]
    }
    return (is.integer(acc))
}

score <- benchmark(iter_benchmark, instance, baseline=baseline_func)


native_mem_vec.delete_instance()
return (score)
