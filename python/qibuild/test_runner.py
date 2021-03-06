import datetime
import multiprocessing
import os
import re
import sys

from qisys import ui
from qisys.qixml import etree
import qisys.command
import qitest.conf
import qitest.runner

class ProjectTestRunner(qitest.runner.TestSuiteRunner):
    """ Implements :py:class:`.TestSuiteRunner` for a qibuild/cmake project """

    def __init__(self, project):
        self.project = project
        self.perf = False
        self.nightly = False
        self.nightmare = False
        self._pattern = None
        self._coverage = False
        self._valgrind = False
        self._num_cpus = -1
        tests = qitest.conf.parse_tests(project.qitest_json)
        super(ProjectTestRunner, self).__init__(tests)
        for directory in (self.test_results_dir,
                          self.perf_results_dir):
            qisys.sh.rm(directory)
            qisys.sh.mkdir(directory)

    @property
    def launcher(self):
        """ Implements TestSuiteRunner.launcher """
        return ProcessTestLauncher(self)

    @property
    def test_results_dir(self):
        res = os.path.join(self.project.build_directory,
                           "test-results")
        return res

    @property
    def perf_results_dir(self):
        res = os.path.join(self.project.build_directory,
                           "perf-results")
        return res

    @property
    def tests(self):
        """ Override TestSuiteRunner.test to filter perf and nightly tests """
        res =  super(ProjectTestRunner, self).tests
        res = [x for x in res if x.get("perf", False) == self.perf]
        res = [x for x in res if x.get("nightly", False) == self.nightly]
        return res

    @property
    def num_cpus(self):
        return self._num_cpus

    @num_cpus.setter
    def num_cpus(self, value):
        if value == -1:
            return
        if not qisys.command.find_program("taskset"):
            mess = "taskset was not found on the system.\n"
            mess += "Cannot set number of CPUs used by the tests"
            raise Exception(mess)
        self._num_cpus = value

    @property
    def valgrind(self):
        return self._valgrind

    @valgrind.setter
    def valgrind(self, value):
        if not value:
            return
        if not qisys.command.find_program("valgrind"):
            raise Exception("valgrind was not found on the system")
        self._valgrind = value

    @property
    def coverage(self):
        return self._coverage

    @coverage.setter
    def coverage(self, value):
        if not value:
            return
        if not qisys.command.find_program("gcovr"):
            raise Exception("please install gcovr in order to measure coverage")


class ProcessTestLauncher(qitest.runner.TestLauncher):
    """ Implements :py:class:`.TestLauncher` using
    :py:class:`qisys.command.Process`

    """
    def __init__(self, project_runner):
        self.suite_runner = project_runner
        self.project = self.suite_runner.project
        self.verbose = self.suite_runner.verbose
        self.valgrind_log = None
        self.perf_out = None
        self.test_out = None

    def launch(self, test):
        """ Implements :py:func:`qitest.runner.TestLauncher.launch`

        Also make sure a Junit-like XML file is always written, even
        if the test did not produce any XML file on its own or crashed
        before being able to write one.

        """
        self.perf_out = os.path.join(self.suite_runner.perf_results_dir,
                                     test["name"] + ".xml")
        self.test_out = os.path.join(self.suite_runner.test_results_dir,
                                     test["name"] + ".xml")
        res = qitest.result.TestResult(test)
        self._update_test(test)
        cmd = test["cmd"]
        timeout = test["timeout"]
        env = test["env"]
        cwd = test["working_directory"]
        process = qisys.command.Process(cmd, cwd=cwd, env=env)
        start = datetime.datetime.now()
        process.run(timeout)
        end = datetime.datetime.now()
        delta = end - start

        res.time = float(delta.microseconds) / 10 ** 6 + delta.seconds
        res.out = process.out
        # Sometimes the process did not have any output,
        # but we still want to let the user know it ran
        if not process.out:
            res.out = "<no output>"

        message = self.get_message(process, timeout=timeout)
        if process.return_type == qisys.command.Process.OK:
            res.ok = True
            if self.verbose:
                ui.info("\n", process.out)
            message = (ui.green, message)
        elif process.return_type == qisys.command.Process.INTERRUPTED:
            res.ok = None
            message = (ui.brown, "interrupted")
        else:
            ui.info("\n", process.out)
            message = (ui.red, message)

        res.message = message
        self._post_run(res, test)
        return res

    def _update_test(self, test):
        """ Update the test given the settings on the test suite """
        self._update_test_cmd_for_project(test)
        self._update_test_executable(test)
        self._update_test_env(test)
        self._update_test_cwd(test)
        valgrind = self.suite_runner.valgrind
        if valgrind:
            self._with_valgrind(test)
        num_cpus = self.suite_runner.num_cpus
        if num_cpus != -1:
            self._with_num_cpus(test, num_cpus)

    def _update_test_cmd_for_project(self, test):
        if not self.project:
            return
        perf_results = os.path.join(self.project.build_directory,
                                    "perf-results")
        if test.get("gtest"):
            cmd = test["cmd"]
            cmd.append("--gtest_output=xml:%s" % self.test_out)
        if test.get("perf"):
            qisys.sh.mkdir(perf_results)
            cmd = test["cmd"]
            cmd.extend(["--output", self.perf_out])

    def _update_test_executable(self, test):
        """ Sometimes the path to the executable to run is a
        relative path to the suite runner working directory

        """
        cmd = test["cmd"]
        executable = cmd[0]
        executable = os.path.join(self.suite_runner.cwd, cmd[0])
        cmd[0] = executable

    def _update_test_env(self, test):
        build_env = os.environ.copy()
        if self.suite_runner.env:
            build_env = self.suite_runner.env.copy()
        test_env = test.get("environment")
        if test_env:
            build_env.update(test_env)
        envsetter = qisys.envsetter.EnvSetter(build_env=build_env)
        if ui.config_color(sys.stdout):
            envsetter.set_env_var("GTEST_COLOR", "yes")
        sdk_dir = self.project.sdk_directory
        if os.name == 'nt':
            bin_dir = os.path.join(sdk_dir, "bin")
            envsetter.prepend_to_path(bin_dir)
        if sys.platform == "darwin":
            lib_dir = os.path.join(sdk_dir, "lib")
            envsetter.prepend_directory_to_variable(lib_dir, "DYLD_LIBRARY_PATH")
            envsetter.prepend_directory_to_variable(sdk_dir, "DYLD_FRAMEWORK_PATH")
        env = envsetter.get_build_env()
        test["env"] =  env

        # Quick hack:
        gtest_repeat = env.get("GTEST_REPEAT", "1")
        test["timeout"] = test["timeout"] * int(gtest_repeat)

    def _update_test_cwd(self, test):
        cwd = self.suite_runner.cwd
        if test.get("working_directory") is None:
            test["working_directory"] = cwd
        print test["working_directory"]

    def _with_valgrind(self, test):
        if not qisys.command.find_program("valgrind"):
            raise Exception("valgrind was not found on the system")
        cwd = test["working_directory"]
        self.valgrind_log = os.path.join(cwd, test["name"] + "_valgrind.log")
        test["timeout"] = test["timeout"] * 10
        test["cmd"] = ["valgrind", "--track-fds=yes",
                       "--log-file=%s" % self.valgrind_log] + test["cmd"]

    def _with_num_cpus(self, test, num_cpus):
        cpu_list = get_cpu_list(multiprocessing.cpu_count(),
                                num_cpus, self.worker_index)
        taskset_opts = ["-c", ",".join(str(i) for i in cpu_list)]
        test["cmd"] = ["taskset"] + taskset_opts + test["cmd"]

    def _post_run(self, res, test):
        if self.suite_runner.valgrind:
            parse_valgrind(self.valgrind_log, res)
        if not res.ok:
            # do not trust generated files:
            qisys.sh.rm(self.perf_out)
            qisys.sh.rm(self.test_out)

        if not res.ok or not os.path.exists(self.test_out):
            self._write_xml(res, test, self.test_out)

    def _write_xml(self, res, test, out_xml):
        """ Make sure a Junit XML compatible file is written """
        # Arbitrary limit output (~700 lines) to prevent from crashing on read
        res.out = res.out[-16384:]
        res.out = re.sub('\x1b[^m]*m', "", res.out)

        # Windows output is most likely code page 850
        if sys.platform.startswith("win"):
            encoding = "ascii"
        else:
            encoding = "UTF-8"
        try:
            res.out = res.out.decode(encoding, "ignore")
        except UnicodeDecodeError:
            pass
        # Make sure there are no invalid data in the XML
        res.out = qisys.qixml.sanitize_xml(res.out)

        if res.ok:
            num_failures = "0"
        else:
            num_failures = "1"
        message_as_string = " ".join(str(x) for x in res.message
                                     if not isinstance(x, ui._Color))

        root = etree.Element("testsuites")
        root.set("tests", "1")
        root.set("failures", num_failures)
        root.set("disabled", "0")
        root.set("errors", "0")
        root.set("time", str(res.time))
        root.set("name", "All")
        test_suite = etree.SubElement(root, "testsuite")
        test_suite.set("name", "test")
        test_suite.set("tests", "1")
        test_suite.set("failures", num_failures)
        test_suite.set("disabled", "0")
        test_suite.set("errors", "0")
        test_suite.set("time", str(res.time))
        test_case = etree.SubElement(test_suite, "testcase")
        test_case.set("name", test["name"])
        test_case.set("status", "run")
        if not res.ok:
            failure = etree.SubElement(test_case, "failure")
            failure.set("message", message_as_string)
            failure.text = res.out

        qisys.qixml.write(root, out_xml, encoding=encoding)

    def get_message(self, process, timeout=None):
        """ Human readable string describing the state of the process """
        if process.return_type == qisys.command.Process.OK:
            return "[OK]"
        if process.return_type == qisys.command.Process.INTERRUPTED:
            return "Interrupted"
        if process.return_type == qisys.command.Process.NOT_RUN:
            mess = "Not run"
            if process.exception is not None:
                mess += ": " + str(process.exception)
            return mess
        if process.return_type == qisys.command.Process.TIME_OUT:
            return "Timed out (%is)" % timeout
        if process.return_type == qisys.command.Process.ZOMBIE:
            return "Zombie (Timeout = %is)" % timeout
        if process.return_type == qisys.command.Process.FAILED:
            retcode = process.returncode
            if retcode > 0:
                return "[FAIL] Return code: %i" % retcode
            else:
                return qisys.command.str_from_signal(-retcode)


def get_cpu_list(total_cpus, num_cpus_per_test, worker_index):
    cpu_list = list()
    i = worker_index * num_cpus_per_test
    cpu_list = range(i, i + num_cpus_per_test)
    cpu_list = [i % total_cpus for i in cpu_list]
    return cpu_list


def parse_valgrind(valgrind_log, res):
    """ Parse valgrind logs and extract interesting errors. """
    message = ""
    leak_fd_regex      = re.compile("==\d+== FILE DESCRIPTORS: (\d+)")
    invalid_read_regex = re.compile("==\d+== Invalid read of size (\d+)")
    with open(valgrind_log, "r") as f:
        lines = f.readlines()

    for l in lines:
        res.out += l
        r = leak_fd_regex.search(l)
        if r:
            fdopen = int(r.group(1))
            # 4: in/out/err + valgrind_log
            if fdopen > 4:
                res.ok = False
                message += "Error file descriptor leaks: " + str(fdopen - 4) + "\n"
            continue
        r = invalid_read_regex.search(l)
        if r:
            res.ok = False
            message += "Invalid read " + r.group(1) + "\n"
    ui.info(ui.red, message)
