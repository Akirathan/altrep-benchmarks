import mx
import mx_benchmark
from mx_benchmark import StdOutBenchmarkSuite
from typing import Tuple, List, Dict, Union, Any
import re
import os
from pathlib import Path
import subprocess
from enum import Enum

# Can be run only from FastR suite, cannot be run directly.

_suite = mx.suite("altrep-benchmarks")
_fastr_suite = mx.suite("fastr", fatalIfMissing=True)


class AltrepBenchmarkSuite(StdOutBenchmarkSuite):
    class OutputCapture:
        def __init__(self):
            self.current_benchmark: str = None
            self.start_pattern = re.compile(r"^executing benchmark (?P<benchmark>[a-zA-Z0-9\.\-_]+) .*")
            self.markdict: Dict[str, str] = {}

        def __call__(self, text: str):
            print(text)
            match = re.match(self.start_pattern, text)
            if match:
                bm_name = match.group(1)
                self.current_benchmark = bm_name
                self.markdict[self.current_benchmark] = ""
            else:
                if self.current_benchmark is not None:
                    self.markdict[self.current_benchmark] += text
    
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
    
    def benchmarkList(self, bmSuiteArgs: List[str]) -> List[str]:
        return [
            "iterate-native-mem-vec",
            "iterate-dataptr",
            "iterate-elt",
            "iterate-generator",
            "native-dataptr-before-native-mem-vec",
            "native-dataptr-before-vec-wrapper",
            "native-dataptr-before-vec-wrapper-elt",
            "native-dataptr-inside-native-mem-vec",
            "native-dataptr-inside-vec-wrapper",
            "native-dataptr-inside-vec-wrapper-elt",
            "native-iter-by-region-native-mem-vec",
            "native-iter-by-region-vec-wrapper",
            "native-iter-by-region-vec-wrapper-elt",
            "native-iter-by-region-vec-wrapper-get-region",
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

        bench_runner_script = os.path.join(mx.project("altrep.benchmarks").dir, "bench-runner.r")
        bench_name = benchmarks[0]
        bench_path = os.path.join(mx.project("altrep.benchmarks").dir, bench_name + ".r")

        bench_runner_args = [
            "--slave",
            "--vanilla",
            "-f", bench_runner_script,
            "--args",
            "--baseline", "TRUE" if self._bench_args.run_with_baseline else "FALSE",
            "--iterations", str(self._bench_args.iterations),
            "--length", str(self._bench_args.data_length),
            "--warmup", str(self._bench_args.warmup),
            "--measure", str(self._bench_args.measure),
            bench_path
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

        dims = {
            "config.data-length": self._bench_args.data_length,
            "config.warmup": self._bench_args.warmup,
            "config.measure": self._bench_args.measure
        }

        return retcode, output_capture, dims
    
    def vmArgs(self, bmSuiteArgs: List[str]) -> List[str]:
        return self.vm_args
    
    def runArgs(self, bmSuiteArgs: List[str]) -> List[str]:
        return self.run_args

    def validateReturnCode(self, retcode: int) -> bool:
        return True
    
    def validateStdoutWithDimensions(self, out: OutputCapture, benchmarks: List[str], bmSuiteArgs: List[str], retcode: int,
                                     dims: Dict[str, str]) -> List[Any]:
        datapoints = []
        for bm_name, bm_output in out.markdict.items():
            try:
                datapoint = super().validateStdoutWithDimensions(bm_output, benchmarks, bmSuiteArgs, dims=dims)
                assert len(datapoint) <= 2
                if len(datapoint) == 2:
                    assert "baseline.score" in datapoint[1]
                    datapoint[0].update(datapoint[1])
                datapoints.append(datapoint[0])
            except RuntimeError:
                print("Benchmark " + bm_name + " failed")
        return datapoints
    
    def successPatterns(self):
        return [
            re.compile(r"^([a-zA-Z0-9\-_]+)[ ]*: ([0-9]+(?:\.[0-9]+)?)", re.MULTILINE)
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
    
    def rules(self, out: OutputCapture, benchmarks: List[str], bmSuiteArgs: List[str]) -> [mx_benchmark.StdOutRule]:
        host_vm, host_vm_config = self._get_host_vm_tuple()
        host_vm_backend = "NA"
        if self._run_in_fastr:
            if "FASTR_RFFI" in os.environ:
                host_vm_backend = os.environ["FASTR_RFFI"]
            else:
                host_vm_backend = "nfi"
        return [
            mx_benchmark.StdOutRule(
                r"^(?P<benchmark>[a-zA-Z0-9\-_]+)[ ]*: (?P<score>[0-9]+(?:\.[0-9]+)?)",
                {
                    "vm": "fastr" if self._run_in_fastr else "gnur",
                    "config.name": "core" if mx.suite("compiler", fatalIfMissing=False) else "default",
                    "host-vm": host_vm,
                    "host-vm-config": host_vm_config,
                    "host-vm-backend": host_vm_backend,
                    "benchmark": ("<benchmark>", str),
                    "metric.name": "throughput",
                    "metric.value": ("<score>", float),
                    "metric.score-function": "id",
                    "metric.better": "higher",
                }
            ),
            mx_benchmark.StdOutRule(
                r"^baseline score[ ]*:[ ]*(?P<baseline_score>[0-9]+(?:\.[0-9]+)?)",
                {
                    "baseline.score": ("<baseline_score>", float),
                }
            )
        ]
    
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
        if not self._is_package_installed("altreprffitests"):
            pkg_path = \
                self._fastr_dir.joinpath("com.oracle.truffle.r.test.native", "packages", "altreprffitests", "altreprffitests")
            assert pkg_path.exists(), "Cannot find altreprffi package"
            self._clean_package(pkg_path)
            self._install_package(pkg_path)

        if not self._is_package_installed("altrepbench"):
            pkg_path = \
                self._fastr_dir.joinpath("..", "altrep-benchmarks", "native_bench_pkg")
            assert pkg_path.exists(), "Cannot find altrepbench package"
            self._clean_package(pkg_path)
            self._install_package(pkg_path)

    def _is_package_installed(self, package: str) -> bool:
        libdir = self._fastr_dir.joinpath("library") if self._run_in_fastr else self._gnur_dir.joinpath("library")
        for installed_pkg in libdir.iterdir():
            if installed_pkg.name == package:
                return True
        return False
    
    def _install_package(self, pkgpath: Path) -> None:
        print(f"Installing package {pkgpath}")
        pkg_abspath = str(pkgpath.resolve().absolute())
        if self._run_in_fastr:
            _fastr_suite.extensions.do_run_r(["CMD", "INSTALL", pkg_abspath], "R")
        else:
            gnur_bin = str(self._gnur_dir.joinpath("bin", "R").absolute())
            self._run_with_check([gnur_bin, "CMD", "INSTALL", pkg_abspath])
    
    def _clean_package(self, pkgpath: Path) -> None:
        print(f"Cleaning package in {pkgpath}")
        src_dir = pkgpath.joinpath("src")
        assert src_dir.exists()
        for src_file in src_dir.iterdir():
            if src_file.name.endswith(".o") or src_file.name.endswith(".so"):
                src_file.unlink()

    def _run_with_check(self, cmd: List[str], **kwargs) -> None:
        print(f"Running {cmd}")
        subprocess.run(cmd, check=True, **kwargs)



def altrep_benchmark(args):
    return mx_benchmark.benchmark(["altrep"] + args)

mx_benchmark.add_bm_suite(AltrepBenchmarkSuite())
