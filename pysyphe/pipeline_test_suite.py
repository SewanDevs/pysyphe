# -*- coding: utf-8 -*-

from six import with_metaclass

import types
import pytest
from mock import MagicMock

from .actions import Action
from .transactions import TransactionsManager, PipelineTransactionHandler
from .exceptions import PysypheException

"""
    Pipeline Testing How-To:

    To test a pipeline, inherit from PipelineTestSuite in your test file and implements pipeline_creator and success_checker.
    The name of the class you have created should begin with 'Test' for pytest to collect it.
    pipeline_creator and success_checker have to be staticmethod.
    pipeline_creator should return a ActionPipeline instance. Every calls to this function should return a fresh pipeline.
    success_checker should return a boolean.
    To add a function fixture to all tests, decorate your inherited class with pytest.mark.usefixtures().

    ```python
    import pytest
    from pipeline_helper import PipelineTestSuite
    import pipelines

    @pytest.mark.usefixtures("fixture_name")
    class TestPipeline(PipelineTestSuite):
        @staticmethod
        def pipeline_creator():
            return pipelines.generate_pipeline_to_test()

        @staticmethod
        def success_checker():
            return pipelines.check_rollback_was_successfull()
    ```

    TODO: success_checker
"""


# This exception should be used or catched by anyone, so we define it here.
class _PipelineTestSuiteActionException(PysypheException):
    pass


def _copy_func(func):
    return types.FunctionType(
        func.__code__,
        func.__globals__,
        func.__name__,
        func.__defaults__,
        func.__closure__,
    )


class _PipelineTestSuiteMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        # As described in the comment of PipelineTestSuite.pipeline_with_failure_fixture (you should look at it before),
        # we need to re-parametrize pipeline_with_failure_fixture in the subclasses because the params depends on the return value
        # of the implementations of pipeline_creator in thoses subclasses.
        pipeline_to_test = None
        if "pipeline_creator" in attrs:
            pipeline_creator = attrs["pipeline_creator"]
            pipeline_to_test = pipeline_creator.__func__()
        if pipeline_to_test:
            # The class currently constructed defines a pipeline to test.
            fixture_params = range(len(pipeline_to_test.actions))
            # Now, we need to retrieve pipeline_with_failure_fixture to re-parametrize it.
            # It is somewhere in the baseclasses, at least one have it or we are not somewhere in the inheritence tree
            # of PipelineTestSuite.
            pipeline_with_failure_fixture = [
                base.pipeline_with_failure_fixture
                for base in bases
                if hasattr(base, "pipeline_with_failure_fixture")
            ]
            pipeline_with_failure_fixture = pipeline_with_failure_fixture[0]
            # Now that we have it, we will make a copy of it to avoid breaking the parametrization of other subclasses.
            # To understand why, you should know that pytest saves the parametrization of a fixture as metadata on the original
            # function and thus if we re-parametrize the same fixture again, all subclasses will overwrite the same params.
            copied_func = _copy_func(pipeline_with_failure_fixture)
            attrs["pipeline_with_failure_fixture"] = pytest.fixture(
                scope="function", params=fixture_params
            )(copied_func)
        # We have another problem, pytest.mark.usefixtures on subclasses is buggy actually:
        # See: https://github.com/pytest-dev/pytest/issues/2806, https://github.com/pytest-dev/pytest/issues/568 and
        # https://github.com/pytest-dev/pytest/issues/535.
        # So, for each test function in the bases, we make a copy on the current class to permit the use of usefixtures.
        for base in bases:
            for attr_name, attr in vars(base).items():
                if attr_name.startswith("test") and callable(attr):
                    copied_func = _copy_func(attr)
                    if (
                        attr_name not in attrs
                    ):  # We want to avoid overwriting something.
                        attrs[attr_name] = copied_func
        return type.__new__(mcs, name, bases, attrs)


class PipelineTestSuite(with_metaclass(_PipelineTestSuiteMetaclass, object)):
    @staticmethod
    # pipeline_creator is called at metaclass instanciation time so it needs to be static
    def pipeline_creator():
        """ To be reimplemented """
        return None

    @staticmethod
    def success_checker():
        """ To be reimplemented """
        return True

    @staticmethod
    def modify_action(pipeline, action, position):
        pipeline._actions_pipeline._list[position] = action

    @pytest.fixture(scope="function")
    def pipeline_fixture(self):
        if not self.success_checker():
            # TODO: maybe it should fail... Because skipped test are not seen by developers.
            pytest.skip("Last test has not been correctly cleaned up...")
        yield self.pipeline_creator()

    @pytest.fixture(scope="function", params=[])
    # We know that there is currently no pipeline to test so the params of the fixture are empty.
    # But, in subclasses, the pipeline to test will not be empty and the fixture should re-parametrized.
    # This is done thanks to the metaclass PipelineTestSuiteMetaclass.
    def pipeline_with_failure_fixture(self, pipeline_fixture, request):
        action_pos_that_fails = request.param
        action_fct = MagicMock(
            side_effect=_PipelineTestSuiteActionException(
                "Your pipeline has been eaten by your dog ! Try again."
            )
        )
        failed_action = Action(action_fct, lambda: None)
        self.modify_action(pipeline_fixture, failed_action, action_pos_that_fails)
        yield pipeline_fixture

    def test_pipeline__complete(self, pipeline_fixture):
        trm = TransactionsManager()
        pipe_handler = PipelineTransactionHandler(pipeline_fixture)
        trm.add_transaction_handler(pipe_handler)
        with trm.begin():
            trm.execute()
            trm.rollback()
        assert self.success_checker()

    def test_pipeline__partial_fails(self, pipeline_with_failure_fixture):
        trm = TransactionsManager()
        pipe_handler = PipelineTransactionHandler(pipeline_with_failure_fixture)
        trm.add_transaction_handler(pipe_handler)
        with pytest.raises(
            _PipelineTestSuiteActionException
        ):  # Exception of failed action mock.
            with trm.begin():
                trm.execute()
        assert self.success_checker()
