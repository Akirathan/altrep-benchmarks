native_mem_vec.create_instance <- function(data_length) {
    .Call("native_mem_vec_create_instance", data_length)
}

native_mem_vec.delete_instance <- function() {
    .Call("native_mem_vec_delete_instance")
}

generator_altvec.new <- function(data_length, fn) {
    stopifnot( is.symbol(fn))
    stopifnot( length(data_length) == 1)

    .Call("generator_altvec_new", as.integer(data_length), fn, parent.frame())
}
