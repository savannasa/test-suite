"""
Main integration for llvm-lit: This defines a lit test format.
Also contains logic to load benchmark modules.
"""
import lit
import lit.TestRunner
import lit.util
import lit.formats
import litsupport.modules
import litsupport.modules.hash
import litsupport.testfile
import litsupport.testplan
import logging
import os


SKIPPED = lit.Test.ResultCode('SKIPPED', False)
NOEXE = lit.Test.ResultCode('NOEXE', True)


class TestContext:
    """This class is used to hold data used while constructing a testrun.
    For example this can be used by modules modifying the commandline with
    extra instrumentation/measurement wrappers to pass the filenames of the
    results to a final data collection step."""
    def __init__(self, test, litConfig, tmpDir, tmpBase):
        self.test = test
        self.config = test.config
        self.litConfig = litConfig
        self.tmpDir = tmpDir
        self.tmpBase = tmpBase


class TestSuiteTest(lit.formats.ShTest):
    def __init__(self):
        super(TestSuiteTest, self).__init__()

    def execute(self, test, litConfig):
        config = test.config
        if config.unsupported:
            return lit.Test.Result(Test.UNSUPPORTED, 'Test is unsupported')
        if litConfig.noExecute:
            return lit.Test.Result(Test.PASS)

        # Parse .test file and initialize context
        tmpDir, tmpBase = lit.TestRunner.getTempPaths(test)
        lit.util.mkdir_p(os.path.dirname(tmpBase))
        context = TestContext(test, litConfig, tmpDir, tmpBase)
        litsupport.testfile.parse(context, test.getSourcePath())
        plan = litsupport.testplan.TestPlan()

        # Report missing test executables.
        if not os.path.exists(context.executable):
            return lit.Test.Result(NOEXE, "Executable '%s' is missing" %
                                   context.executable)

        # Skip unchanged tests
        if config.previous_results:
            litsupport.modules.hash.compute(context)
            if litsupport.modules.hash.same_as_previous(context):
                result = lit.Test.Result(
                        SKIPPED, 'Executable identical to previous run')
                val = lit.Test.toMetricValue(context.executable_hash)
                result.addMetric('hash', val)
                return result

        # Let test modules modify the test plan.
        for modulename in config.test_modules:
            module = litsupport.modules.modules.get(modulename)
            if module is None:
                raise Exception("Unknown testmodule '%s'" % modulename)
            module.mutatePlan(context, plan)

        # Execute Test plan
        result = litsupport.testplan.executePlanTestResult(context, plan)

        return result
