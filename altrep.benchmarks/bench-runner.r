get_cur_seconds <- function() {
    proc.time()[3]
}

#' Returns a score of a benchmarked function. This score is dependent on the duration of one
#' benchmarking function call. The higher the score, the better the performance.
#'
#' @param benchmark_func A function to be measured
#' @param benc_func_args Arguments to the benchmarking function
#' @param warmup_time Time in seconds for warmup
#' @param measure_time Time in seconds for measure
#' @param baseline_func Baseline function
benchmark <- function(benchmark_func, bench_func_args,
                      warmup_time = WARMUP_TIME, measure_time = MEASURE_TIME,
                      baseline_func = NULL)
{
    if (!is.null(baseline_func) && RUN_WITH_BASELINE) {
        cat("running baseline\n")
        baseline_score <- benchmark(baseline_func, bench_func_args, warmup_time, measure_time)
        cat("baseline score:", baseline_score, "\n")
    }

    in_warmup <- TRUE
    cat(warmup_time, "seconds warmup started\n")
    run_count <- 0
    target_time <- warmup_time
    start_time <- get_cur_seconds()

    while (TRUE) {
        if (!benchmark_func(bench_func_args)) {
            cat(if (in_warmup) "WARMUP" else "MEASURE", "ERROR: wrong result\n")
            return (0)
        }
        run_count <- run_count + 1

        if (get_cur_seconds() - start_time >= target_time) {
            if (in_warmup) {
                cat("warmup finished after", run_count, "steps\n")

                # Start measurement phase
                target_time <- measure_time
                in_warmup <- FALSE
                cat(target_time, "seconds measurement started\n")
                run_count <- 0
                start_time <- get_cur_seconds()
            } else {
                break
            }
        }
    }

    end_time <- get_cur_seconds()
    delta_time <- end_time - start_time
    step_time <- delta_time / run_count
    score <- 1 / step_time
    cat("measure finished after", run_count, "steps in", round(delta_time, 1), "seconds\n")
    invisible (score)
}


# argparser library is used just for benchmark runner.
if (!require(argparser, quietly=TRUE)) {
    # TODO: Vytahnout do mx_altrepbench.py
    install.packages("argparser")
}
require(argparser, quietly=TRUE)
# Load other libraries necessary for running benchmarks.
stopifnot( require(altreprffitests, quietly=TRUE))
stopifnot( require(altrepbench, quietly=TRUE))

parser <- arg_parser("Benchmark runner")
parser <- add_argument(parser, "--length", help="Data length", default=1e7)
parser <- add_argument(parser, "--warmup", help="Warmup time in seconds", default=1)
parser <- add_argument(parser, "--measure", help="Meausre time in seconds", default=1)
parser <- add_argument(parser, "--baseline", help="Whether baseline should be run", default=TRUE)
parser <- add_argument(parser, "--iterations", help="This is useful only to native benchmarks", default=3)
parser <- add_argument(parser, "bench_path", help="Path of a benchmark to be run")

args <- parse_args(parser)
LEN <- as.integer(args$length)
BASELINE_DATA <- as.integer(runif(LEN, min=1, max=100))
WARMUP_TIME <- args$warmup
MEASURE_TIME <- args$measure
RUN_WITH_BASELINE <- args$baseline
ITERATIONS <- as.integer(args$iterations)

bench_path <- args$bench_path
#bench_path <- "/home/pmarek/dev/altrep-benchmarks/altrep.benchmarks/try.r"
bench_name <- tools::file_path_sans_ext(basename(bench_path))

cat("-----\nexecuting benchmark", bench_name, "from file", bench_path, "\n")

ret <- source(bench_path)
score <- ret$value

# This line will be parsed by the mx benchmark runner
cat(bench_name, ":", score, "\n")
