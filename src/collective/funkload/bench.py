import sys
import optparse
import unittest

from zope.testing.testrunner import runner
from zope.testing.testrunner import options

from funkload import BenchRunner
from funkload import FunkLoadTestCase

from collective.funkload import testcase

bench = optparse.OptionGroup(options.parser, BenchRunner.USAGE)
bench.add_option("--url", type="string", dest="main_url",
                  help="Base URL to bench.")
bench.add_option("--cycles", type="string", dest="bench_cycles",
                  help="Cycles to bench, this is a list of number of "
                  "virtual concurrent users, "
                  "to run a bench with 3 cycles with 5, 10 and 20 "
                  "users use: -c 2:10:20")
bench.add_option("--duration", type="string", dest="bench_duration",
                  help="Duration of a cycle in seconds.")
bench.add_option("--sleep-time-min", type="string",
                  dest="bench_sleep_time_min",
                  help="Minimum sleep time between request.")
bench.add_option("-M", "--sleep-time-max", type="string",
                  dest="bench_sleep_time_max",
                  help="Maximum sleep time between request.")
bench.add_option("--startup-delay", type="string",
                  dest="bench_startup_delay",
                  help="Startup delay between thread.")
bench.add_option("", "--accept-invalid-links", action="store_true",
                  help="Do not fail if css/image links are "
                  "not reachable.")
bench.add_option("", "--simple-fetch", action="store_true",
                  help="Don't load additional links like css "
                  "or images when fetching an html page.")
options.parser.add_option_group(bench)

class FLBenchRunner(BenchRunner.BenchRunner, unittest.TestCase):
                        
    def __init__(self, test, options):
        self.threads = []
        self.module_name = test.__class__.__module__
        self.class_name = test.__class__.__name__
        self.method_name = test._TestCase__testMethodName
        self.options = options
        self.color = not options.no_color
        # create a unittest to get the configuration file
        self.config_path = test._config_path
        self.result_path = test.result_path
        self.class_title = test.conf_get('main', 'title')
        self.class_description = test.conf_get('main', 'description')
        self.test_id = self.method_name
        self.test_description = test.conf_get(self.method_name, 'description',
                                              'No test description')
        self.test_url = test.conf_get('main', 'url')
        self.cycles = map(int, test.conf_getList('bench', 'cycles'))
        self.duration = test.conf_getInt('bench', 'duration')
        self.startup_delay = test.conf_getFloat('bench', 'startup_delay')
        self.cycle_time = test.conf_getFloat('bench', 'cycle_time')
        self.sleep_time = test.conf_getFloat('bench', 'sleep_time')
        self.sleep_time_min = test.conf_getFloat('bench', 'sleep_time_min')
        self.sleep_time_max = test.conf_getFloat('bench', 'sleep_time_max')

        # setup monitoring
        monitor_hosts = []                  # list of (host, port, descr)
        for host in test.conf_get('monitor', 'hosts', '', quiet=True).split():
            host = host.strip()
            monitor_hosts.append((host, test.conf_getInt(host, 'port'),
                                  test.conf_get(host, 'description', '')))
        self.monitor_hosts = monitor_hosts
        # keep the test to use the result logger for monitoring
        # and call setUp/tearDown Cycle
        self.test = test

    def run(self, *args, **kw):
        """Translate from TestCase to BenchRunner"""
        return BenchRunner.BenchRunner.run(self)

    __str__ = BenchRunner.BenchRunner.__repr__

class Runner(runner.Runner):

    def configure(self):
        result = super(Runner, self).configure()
        self.options.no_color = not self.options.color
        return result

    def register_tests(self, tests):
        """Wrap each found test in the Funkload bench runner."""
        self.convertFLTests(tests)
        return super(Runner, self).register_tests(tests)

    def convertFLTests(self, tests):
        for layer, suite in tests.iteritems():
            for test in suite:
                if isinstance(test,
                              FunkLoadTestCase.FunkLoadTestCase):
                    idx = suite._tests.index(test)
                    suite._tests.remove(test)
                    suite._tests.insert(idx, FLBenchRunner(test, self.options))

def run(defaults=None, args=None):
    runner = Runner(defaults, args)
    testcase.patch()
    runner.run()
    testcase.unpatch()
    if runner.failed and runner.options.exitwithstatus:
        sys.exit(1)
    return runner.failed
    
