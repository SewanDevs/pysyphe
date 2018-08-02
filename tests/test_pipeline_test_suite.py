# -*- coding: utf-8 -*-

import pytest
from mock import MagicMock

from pysyphe.actions import statefull_action, ActionsPipeline
from pysyphe.streamers import InfoStreamer
from pysyphe.pipeline_test_suite import PipelineTestSuite


# Principle of this test: we will make a two-actions-long pipeline and use the infostreamer to know what was executed/rollbacked.


class InfoStreamerMock(InfoStreamer):
    def __init__(self):
        self.steps = []

    def send_info(self, **kwargs):
        if "begin" in kwargs:
            step_type = "begin"
        if "end" in kwargs:
            step_type = "end"
        self.steps.append((kwargs["action_name"], step_type))


info_streamer = InfoStreamerMock()


def pipeline_gen():
    @statefull_action([], name="action1")
    def action1(state):
        pass

    @action1.rollback_action([], name="rollback1")
    def rollback1(state):
        pass

    @statefull_action([], name="action2")
    def action2(state):
        pass

    @action2.rollback_action([], name="rollback2")
    def rollback2(state):
        pass

    ap = ActionsPipeline(name="pipeline")
    ap.rollback_name = "pipeline_rollback"
    ap.append(action1.get_prepared_action())
    ap.append(action2.get_prepared_action())
    ap.set_info_streamer(info_streamer)
    return ap


@pytest.fixture(scope="module")
def validate_test():
    yield
    # Tests has been done, we can validate now.
    # With a two-long pipeline, there is three tests: one complete, and one that makes each action fail.
    # PipelineTestSuite replace an action of the pipeline by a fake action (that does not call the infostreamer).
    complete_test_steps = [
        ("pipeline", "begin"),
        ("action1", "begin"),
        ("action1", "end"),
        ("action2", "begin"),
        ("action2", "end"),
        ("pipeline", "end"),
        ("pipeline_rollback", "begin"),
        ("rollback2", "begin"),
        ("rollback2", "end"),
        ("rollback1", "begin"),
        ("rollback1", "end"),
        ("pipeline_rollback", "end"),
    ]
    # partial2: second action is replaced
    partial1_test_steps = [
        ("pipeline", "begin"),
        ("action1", "begin"),
        ("action1", "end"),
        ("pipeline", "end"),
        ("pipeline_rollback", "begin"),
        ("rollback1", "begin"),
        ("rollback1", "end"),
        ("pipeline_rollback", "end"),
    ]
    # partial2: first action is replaced
    partial2_test_steps = [
        ("pipeline", "begin"),
        ("pipeline", "end"),
        ("pipeline_rollback", "begin"),
        ("pipeline_rollback", "end"),
    ]
    # We will use string comparison to look for sublist :D
    complete_test_steps = ",".join(["-".join(step) for step in complete_test_steps])
    partial1_test_steps = ",".join(["-".join(step) for step in partial1_test_steps])
    partial2_test_steps = ",".join(["-".join(step) for step in partial2_test_steps])
    done_steps = ",".join(["-".join(step) for step in info_streamer.steps])
    assert complete_test_steps in done_steps
    assert partial1_test_steps in done_steps
    assert partial2_test_steps in done_steps


# /!\ DISCLAIMER /!\ Sorry, but you can't call TestPipelineTestSuite partially, you have to call all tests.
@pytest.mark.usefixtures("validate_test")
class TestPipelineTestSuite(PipelineTestSuite):
    @staticmethod
    def pipeline_creator():
        return pipeline_gen()


def test_skip_if_not_clean(monkeypatch):
    skip_mock = MagicMock()
    monkeypatch.setattr("pytest.skip", skip_mock)
    monkeypatch.setattr(
        PipelineTestSuite, "success_checker", MagicMock(return_value=False)
    )
    # fixture are generator. Need to call next on it for the body to be executed.
    next(PipelineTestSuite().pipeline_fixture())
    assert skip_mock.called
