instance <- simple_vec_wrapper.create_instance(BASELINE_DATA, gen.Elt=TRUE)

# altrep Elt method invocation
iter_benchmark <- function(instance) {
    acc <- 0L
    len <- length(instance)
    for (i in 1:(len - 1L)) {
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

benchmark(iter_benchmark, instance, baseline=baseline_func)