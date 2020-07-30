import mx
import mx_benchmark
from mx_benchmark import StdOutBenchmarkSuite
from typing import Tuple, List, Dict, Union, Any
import re
import os
from pathlib import Path
import subprocess
from enum import Enum
import tempfile
import numpy as np
from statistics import geometric_mean

# Can be run only from FastR suite, cannot be run directly.

_suite = mx.suite("altrep-benchmarks")
_fastr_suite = mx.suite("fastr", fatalIfMissing=True)


class AltrepBenchmarkSuite(StdOutBenchmarkSuite):
    class OutputCapture:
        def __init__(self):
            self._start_pattern = re.compile(r"^benchmark results:")
            self._reading_bench_header = False
            self._reading_bench_timestamps = False
            self._print_limit = 100
            self._print_count = 0
            self.start_time = 0.0
            self.end_time = 0.0
            self.steps = 0
            self.timestamps: List[float] = []

        def _print(self, text):
            if self._print_count <= self._print_limit:
                print(text)
            self._print_count += 1

        def __call__(self, text: str):
            text = text.strip()
            self._print(text)
            match = re.match(self._start_pattern, text)
            if match:
                self._reading_bench_header = True
                return

            if self._reading_bench_header:
                items = text.split(" ")
                assert len(items) == 3
                self.start_time = float(items[0])
                self.end_time = float(items[1])
                self.steps = int(items[2])
                self._reading_bench_header = False
                self._reading_bench_timestamps = True
                return

            if self._reading_bench_timestamps:
                timestamp = float(text)
                self.timestamps.append(timestamp)

    
    class Driver(Enum):
        FASTR = 1,
        GNUR = 2

    class BenchArgs:
        def __init__(self, driver: "AltrepBenchmarkSuite.Driver", data_length: Union[int, float],
                     iterations: int, baseline: bool, warmup: int, measure: int):
            self.driver = driver
            self.data_length = int(data_length)
            self.iterations = iterations
            self.run_with_baseline = baseline
            self.warmup = warmup
            self.measure = measure
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._run_baseline = False
        self._data_length = 0
        self._iterations = 0
        self.vm_args: List[str] = []
        self.run_args: List[str] = []
        self._fastr_dir: Path = None
        self._gnur_dir: Path = None
        self._native_pkg_bench_pkg_path: Path = None
        self._run_in_fastr = True
        self._bench_args: "AltrepBenchmarkSuite.BenchArgs" = None
        
    def name(self):
        return "altrep"
    
    def group(self):
        # Group should always be Graal for Graal-related projects.
        # Projects such as `compiler` or `fastr` are supposed to be specified in the
        # `subgroup` dimension.
        return "Graal"
    
    def subgroup(self):
        return "fastr"
    
    def version(self):
        return "4"
    
    def benchmarkList(self, bmSuiteArgs: List[str]) -> List[str]:
        return [
            "iterate-native-mem-vec",
            "iterate-native-mem-vec-baseline",
            "iterate-dataptr",
            "iterate-dataptr-baseline",
            "iterate-elt",
            "iterate-elt-baseline",
            "iterate-generator",

            "native-dataptr-before-native-mem-vec",
            "native-dataptr-before-vec-wrapper",
            "native-dataptr-before-vec-wrapper-elt",
            "native-dataptr-before-baseline",

            "native-dataptr-inside-native-mem-vec",
            "native-dataptr-inside-vec-wrapper",
            "native-dataptr-inside-vec-wrapper-elt",
            "native-dataptr-inside-baseline",

            "native-iter-by-region-native-mem-vec",
            "native-iter-by-region-vec-wrapper",
            "native-iter-by-region-vec-wrapper-elt",
            "native-iter-by-region-vec-wrapper-get-region",
            "native-iter-by-region-baseline",

            "try"
        ]

    def before(self, bmSuiteArgs: List[str]) -> None:
        self._fastr_dir = Path(_fastr_suite.dir)
        self._gnur_dir = Path(_fastr_suite.extensions.gnur_path())
        self._native_pkg_bench_pkg_path = Path(_suite.dir).joinpath("native_bench_pkg")
        assert self._fastr_dir.exists()
        assert self._gnur_dir.exists()
        assert self._native_pkg_bench_pkg_path.exists(), "Cannot find nativebench package"

        self._bench_args = self._parse_args(bmSuiteArgs)
        if self._bench_args.driver == AltrepBenchmarkSuite.Driver.FASTR:
            self._run_in_fastr = True
        else:
            self._run_in_fastr = False
        
        self._install_necessary_packages()


    def runAndReturnStdOut(self, benchmarks: List[str], bmSuiteArgs: List[str]) -> Tuple[int, OutputCapture, Dict[str, str]]:
        if len(benchmarks) > 1:
            mx.abort("Only one benchmark can be run at a time")

        bench_name = benchmarks[0]
        bench_path = Path(mx.project("altrep.benchmarks").dir).joinpath(bench_name + ".r")
        bench_runner_source = generate_bench_runner_source(self._bench_args, bench_path)

        with tempfile.NamedTemporaryFile() as bench_runner_script:
            bench_runner_script.write(bytes(bench_runner_source, "UTF-8"))
            bench_runner_script.seek(0)

            bench_runner_args = [
                "--slave",
                "--vanilla",
                "-f", bench_runner_script.name
            ]

            retcode = -1
            output_capture = AltrepBenchmarkSuite.OutputCapture()

            if self._bench_args.driver == AltrepBenchmarkSuite.Driver.FASTR:
                extra_vm_args = []
                extra_vm_args += ["-Dgraal.TraceTruffleCompilation=true"]
                extra_vm_args += ["-Dgraal.CompilationFailureAction=ExitVM"]
                extra_vm_args += ["-da"]
                extra_vm_args += ["-dsa"]
                #os.environ["MX_R_GLOBAL_ARGS"] = " ".join(extra_vm_args)
                self.vm_args = extra_vm_args

                fastr_args = ["--R.PrintErrorStacktracesToFile=true"]

                self.run_args = fastr_args + bench_runner_args

                if mx.suite("compiler", fatalIfMissing=False):
                    os.environ["DEFAULT_DYNAMIC_IMPORTS"] = "graal/compiler"

                retcode = _fastr_suite.extensions.do_run_r(self.run_args, "R", nonZeroIsFatal=False,
                                            extraVmArgs=extra_vm_args, out=output_capture, err=output_capture)
            else:
                # Run in GNU-R
                self.vm_args = []
                self.run_args = bench_runner_args
                gnur_bin = str(self._gnur_dir.joinpath("bin", "R").absolute())
                retcode = mx.run([gnur_bin] + self.run_args, out=output_capture, err=output_capture)

        return retcode, output_capture, None
    
    def vmArgs(self, bmSuiteArgs: List[str]) -> List[str]:
        return self.vm_args
    
    def runArgs(self, bmSuiteArgs: List[str]) -> List[str]:
        return self.run_args

    def validateReturnCode(self, retcode: int) -> bool:
        return True
    
    def validateStdoutWithDimensions(self, out: OutputCapture, benchmarks: List[str], bmSuiteArgs: List[str], retcode: int,
                                     dims: Dict[str, str]) -> List[Any]:

        datapoints = []
        assert len(benchmarks) == 1
        bench_name = benchmarks[0]

        if out.steps > MAX_BENCH_ITERATIONS:
            mx.abort(f"The benchmark {bench_name} did more steps ({out.steps}) than maximum number of iterations ({MAX_BENCH_ITERATIONS}).\n"
                     f"This means for example that the probability of the invocation of GC during the benchmark run is higher than usual.\n"
                     f"Try rerunning the benchmark with smaller warmup time or measure time, or adjust MAX_BENCH_ITERATIONS constant")

        # Filter-out warmup timestamps
        warmup_end = out.start_time + self._bench_args.warmup
        measure_timestamps = [timestamp for timestamp in out.timestamps if timestamp > warmup_end]

        if len(measure_timestamps) < 2:
            mx.abort(f"Less than 2 measurements were done. Run the benchmark with longer measure time (--measure)")

        # Compute final score
        measure_steps = len(measure_timestamps)
        step_time = geometric_mean(np.diff(measure_timestamps))
        # score is number of operations per second
        score = 1 / step_time

        # Find out various machine configuration
        host_vm, host_vm_config = self._get_host_vm_tuple()
        host_vm_backend = "NA"
        if self._run_in_fastr:
            if "FASTR_RFFI" in os.environ:
                host_vm_backend = os.environ["FASTR_RFFI"]
            else:
                host_vm_backend = "nfi"
        
        datapoints.append({
            "vm": "fastr" if self._run_in_fastr else "gnur",
            "config.name": "core" if mx.suite("compiler", fatalIfMissing=False) else "default",
            "config.data-length": self._bench_args.data_length,
            "config.warmup": self._bench_args.warmup,
            "config.measure": self._bench_args.measure,
            "config.iterations": self._bench_args.iterations,
            "host-vm": host_vm,
            "host-vm-config": host_vm_config,
            "host-vm-backend": host_vm_backend,
            "benchmark": bench_name,
            "metric.name": "throughput",
            "metric.value": score,
            "metric.score-function": "id",
            "metric.better": "higher",
            "metric.unit": "op/s",
            "metric.measure-count": str(measure_steps)
        })
        return datapoints
    
    def successPatterns(self):
        return [
            re.compile(r"^benchmark results:", re.MULTILINE)
        ]

    def failurePatterns(self):
        return [
            re.compile(r"Error in"),
            re.compile(r"internal error:"),
            re.compile(r"A fatal error has been detected by the Java Runtime Environment"),
            re.compile(r"Compilation of .* failed"),
            re.compile(r".*at com.oracle.truffle.api.CompilerAsserts.*"),
            re.compile(r"To disable compilation failure notifications"),
            re.compile(r"ERROR: benchmark has returned zero result"),
            re.compile(r"WARMUP ERROR"),
            re.compile(r"MEASURE ERROR"),
        ]
    
    def rules(self, out, benchmarks, bmSuiteArgs):
        return []

    def _get_host_vm_tuple(self) -> Tuple[str, str]:
        if self._run_in_fastr:
            rffi_backend = "-" + os.environ["FASTR_RFFI"] if "FASTR_RFFI" in os.environ else ""
            if mx.suite("compiler", fatalIfMissing=False):
                return ("jvmci", "compiler" + rffi_backend)
            else:
                return ("default", "default")
        else:
            return ("gnur", "nojit")

    def _parse_args(self, bmSuiteArgs: List[str]) -> BenchArgs:
        from argparse import ArgumentParser
        argparser = ArgumentParser()
        argparser.add_argument("-d", "--driver", type=str, default="fastr",
            help="Driver to run - can be either gnur or fastr")
        argparser.add_argument("-i", "--iterations", type=int, default=5,
            help="Number of iterations of outer for-cycle")
        argparser.add_argument("-l", "--length", type=float, default=1e7,
            help="Length of the data")
        argparser.add_argument("-b", "--baseline", action="store_true",
            help="Whether the baseline should also be run, default is run without baseline")
        argparser.add_argument("-w", "--warmup", type=int,
            help="Warmup time in seconds")
        argparser.add_argument("-m", "--measure", type=int,
            help="Measure time in seconds")
        args = argparser.parse_args(bmSuiteArgs)
        driver = None
        if args.driver == "fastr":
            driver = AltrepBenchmarkSuite.Driver.FASTR
        elif args.driver == "gnur":
            driver = AltrepBenchmarkSuite.Driver.GNUR
        else:
            mx.abort(f"Unknown driver {args.driver}")
        return AltrepBenchmarkSuite.BenchArgs(driver, args.length, args.iterations, args.baseline, args.warmup, args.measure)

    def _install_necessary_packages(self) -> None:
        print("========================")
        print(f"Make sure that altreprffitests and altrepbench packages are installed!!!!!")
        print("========================")


MAX_BENCH_ITERATIONS = int(1e8)

def generate_bench_runner_source(bench_args: AltrepBenchmarkSuite.BenchArgs, benchpath: Path) -> str:
    assert benchpath.exists()
    bench_source = benchpath.read_text()
    assert "benchmark_func" in bench_source

    return (
f"stopifnot(require(altreprffitests, quietly=TRUE))\n"
f"stopifnot(require(altrepbench, quietly=TRUE))\n"
f"\n"
f"set.seed(42)\n"
f"\n"
f"LEN <- as.integer({bench_args.data_length})\n"
f"BASELINE_DATA <- as.integer(runif(LEN, min=1, max=100))\n"
f"ITERATIONS <- as.integer({bench_args.iterations})\n"
f"\n"
# bench_source contains a function that will be called in a cycle
f"{bench_source}"
f"\n"
f"get_cur_seconds <- function() {{ proc.time()[[3L]] }}\n"
f"\n"
f"step <- 1L\n"
f"timestamps <- vector('double', {MAX_BENCH_ITERATIONS})\n"
f"cur_seconds <- get_cur_seconds()\n"
f"target_time <- {bench_args.warmup + bench_args.measure}\n"
f"start_time <- cur_seconds\n"
f"\n"
f"while (cur_seconds - start_time < target_time) {{\n"
f"  if (!benchmark_func(benchmark_func_args)) {{\n"
f"    cat('ERROR: Wrong result\\n')\n"
f"    return (0)\n"
f"  }}\n"
f"  timestamps[[step]] <- cur_seconds\n"
f"  step <- step + 1L\n"
f"  cur_seconds <- get_cur_seconds()\n"
f"}}\n"
f"\n"
f"end_time <- get_cur_seconds()\n"
f"\n"
# Output of the benchmark
f"cat('benchmark results:', '\\n')\n"
f"cat(start_time, end_time, step - 1, '\\n')\n"
f"cat(timestamps[1:length(timestamps) < step], sep='\\n')\n"
    )


def altrep_benchmark(args):
    return mx_benchmark.benchmark(["altrep"] + args)

mx_benchmark.add_bm_suite(AltrepBenchmarkSuite())
