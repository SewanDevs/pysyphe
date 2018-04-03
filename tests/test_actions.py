# -*- coding: utf-8 -*-

import sys
import pytest
from copy import copy
from contextlib import contextmanager
from mock import MagicMock

from pysyphe.actions import Action, StatefullAction, statefull_action, UnitAction, unit_action, ActionsPipeline, _format_fct_name
from pysyphe.exceptions import ActionException
from pysyphe.streamers import InfoStreamer
from pysyphe.data_structs import ReferencesDict
if sys.version_info < (3, 0):
    from pysyphe.py2 import InstanceMethod


@contextmanager
def context_manager_mock(action):
    yield


class SharedContextManager(object):
    def __init__(self):
        self.result = ""

    def gen_context_manager(self, before, after):
        @contextmanager
        def cm(action):
            self.result += before
            yield
            self.result += after
        return cm


# TODO: write more tests for format_fct_name
def test__format_fct_name():
    def yolo():
        pass
    assert _format_fct_name(yolo)


class TestUnitAction(object):
    @staticmethod
    def test_init():
        assert Action()

    @staticmethod
    def test_init_2():
        assert Action(lambda: 10, lambda: -10)

    @staticmethod
    def test_name():
        a = Action(lambda: 10)
        a.name = "yolo"
        assert a.name == "yolo"

    @staticmethod
    def test_rollback_name():
        a = Action(lambda: 10)
        a.rollback_name = "yolo"
        assert a.rollback_name == "yolo"

    @staticmethod
    def test_get_name_bad_side():
        with pytest.raises(ActionException):
            Action().get_name("bad_side")

    @staticmethod
    def test_set_name_bad_side():
        with pytest.raises(ActionException):
            Action().set_name("bad_side", "osef")

    @staticmethod
    @pytest.mark.parametrize("action_side", ["action", "rollback"])
    def test_get_name_not_set(monkeypatch, action_side):
        format_fct_name_mock = MagicMock()
        monkeypatch.setattr("pysyphe.actions._format_fct_name", format_fct_name_mock)
        Action().get_name(action_side)
        assert format_fct_name_mock.called

    @staticmethod
    def test_do_nothing():
        with pytest.raises(ActionException):
            Action().do()

    @staticmethod
    def test_do():
        assert Action(lambda: 10).do() == 10

    @staticmethod
    def test_undo_nothing():
        with pytest.raises(ActionException):
            Action().undo()

    @staticmethod
    def test_undo():
        assert Action(lambda: 10, lambda: -10).undo() == -10

    @staticmethod
    @pytest.mark.parametrize("action_type, function_to_call, result", [
        ('action', 'do', 'ba'),
        ('rollback', 'do', ''),
        ('action', 'undo', ''),
        ('rollback', 'undo', 'ba'),
    ])
    def test_add_context_manager(action_type, function_to_call, result):
        ac = Action(lambda: 10, lambda: -10)
        csm = SharedContextManager()
        ac.add_context_manager(action_type, csm.gen_context_manager("b", "a"))
        getattr(ac, function_to_call)()
        assert csm.result == result

    @staticmethod
    @pytest.mark.parametrize("action_type, function_to_call, result", [
        ('action', 'do', 'b2bb3a3aa2'),
        ('rollback', 'do', ''),
        ('action', 'undo', ''),
        ('rollback', 'undo', 'b2bb3a3aa2'),
    ])
    def test_add_context_manager_inner(action_type, function_to_call, result):
        ac = Action(lambda: 10, lambda: -10)
        csm = SharedContextManager()
        ac.add_context_manager(action_type, csm.gen_context_manager("b", "a"))
        ac.add_context_manager(action_type, csm.gen_context_manager("b2", "a2"))
        ac.add_context_manager(action_type, csm.gen_context_manager("b3", "a3"), inner=True)
        getattr(ac, function_to_call)()
        assert csm.result == result

    @staticmethod
    def test_action_context_manager(monkeypatch):
        monkeypatch.setattr(Action, "add_context_manager", MagicMock())
        action = Action()
        assert action.action_context_manager(context_manager_mock)

    @staticmethod
    def test_rollback_context_manager(monkeypatch):
        monkeypatch.setattr(Action, "add_context_manager", MagicMock())
        action = Action()
        assert action.rollback_context_manager(context_manager_mock)

    @staticmethod
    def test_add_context_manager_bad_side():
        with pytest.raises(ActionException):
            Action().add_context_manager("bad_side", "osef")

    @staticmethod
    def test_set_info_streamer_none():
        with pytest.raises(ActionException):
            Action().set_info_streamer(None)

    @staticmethod
    def test_set_info_streamer():
        Action().set_info_streamer(InfoStreamer())

    @staticmethod
    def test_copy():
        a = Action(lambda: 10, lambda: -10)
        a.add_context_manager("action", context_manager_mock)
        a.add_context_manager("rollback", context_manager_mock)
        assert copy(a)

    @staticmethod
    def test_simulate():
        Action(lambda: 10, lambda: -10).simulate()


class TestUnitStateFullAction(object):
    @staticmethod
    def test_init():
        assert StatefullAction()

    @staticmethod
    def test_init_params():
        assert StatefullAction(["test_item"], lambda state: 10)

    @staticmethod
    def test_state_fail():
        with pytest.raises(ActionException):
            StatefullAction().state

    @staticmethod
    def test_state_write():
        with pytest.raises(ActionException):
            action = StatefullAction()
            action.state = {}

    @staticmethod
    def test_action(monkeypatch):
        monkeypatch.setattr(StatefullAction, "_check_fct", MagicMock())
        action = StatefullAction()
        assert action.action(lambda state: 10)

    @staticmethod
    def test_action_not_good(monkeypatch):
        monkeypatch.setattr(StatefullAction, "_check_fct", MagicMock(side_effect=ActionException))
        action = StatefullAction()
        with pytest.raises(ActionException):
            action.action(lambda state: 10)

    @staticmethod
    def test_action_twice(monkeypatch):
        monkeypatch.setattr(StatefullAction, "_check_fct", MagicMock())
        action = StatefullAction()
        action.action(lambda state: 10)
        with pytest.raises(ActionException):
            action.action(lambda state: 10)

    @staticmethod
    def test__check_fct():
        StatefullAction._check_fct(lambda state: 10)

    @staticmethod
    def test__check_fct_not_good():
        with pytest.raises(ActionException):
            StatefullAction._check_fct(lambda: 10)

    @staticmethod
    def test__check_fct_not_good_too():
        with pytest.raises(ActionException):
            StatefullAction._check_fct(lambda state, something_else: 10)

    @staticmethod
    def test__check_fct_not_callable():
        with pytest.raises(ActionException):
            StatefullAction._check_fct(10)

    @staticmethod
    def test_call_no_fct():
        with pytest.raises(ActionException):
            action = StatefullAction()
            action({})

    @staticmethod
    def test_call():
        action = StatefullAction(action_fct=lambda state: 10)
        assert action({}) == 10

    @staticmethod
    def test_call_with_state():
        action = StatefullAction(action_fct=lambda state: 10)
        action._state = {}
        with pytest.raises(ActionException):
            action({})

    @staticmethod
    def test_rollback_action(monkeypatch):
        monkeypatch.setattr(StatefullAction, "_check_fct", MagicMock())
        action = StatefullAction()
        decorator = action.rollback_action()
        decorator(lambda state: 10)
        assert action._rollback_fct({}) == 10

    @staticmethod
    def test_rollback_action_twice(monkeypatch):
        monkeypatch.setattr(StatefullAction, "_check_fct", MagicMock())
        decorator = StatefullAction().rollback_action()
        decorator(lambda state: 10)
        with pytest.raises(ActionException):
            decorator(lambda state: 10)

    @staticmethod
    def test_rollback_action_with_fct(monkeypatch):
        monkeypatch.setattr(StatefullAction, "_check_fct", MagicMock())
        action = StatefullAction()
        action.rollback_action(fct=lambda state: 10)
        assert action._rollback_fct({}) == 10

    @staticmethod
    def test__check_kwargs_for_action():
        action = StatefullAction(["input"])
        action._check_kwargs_for_action({"input": 10})

    @staticmethod
    def test__check_kwargs_for_action_missing():
        action = StatefullAction(["input"])
        with pytest.raises(ActionException):
            action._check_kwargs_for_action({})

    @staticmethod
    def test__check_kwargs_for_action_superfluous():
        action = StatefullAction(["input"])
        with pytest.raises(ActionException):
            action._check_kwargs_for_action({"input": 10, "superfluous": 20})

    @staticmethod
    def test__checks_store_items_for_rollback():
        action = StatefullAction()
        action.rollback_action(["input"], lambda state: 10)
        action._state = {}
        with action._checks_store_items_for_rollback():
            action._state["input"] = 10

    @staticmethod
    def test__checks_store_items_for_rollback_failure_missing():
        action = StatefullAction()
        action.rollback_action(["input"], lambda state: 10)
        action._state = {}
        with pytest.raises(ActionException):
            with action._checks_store_items_for_rollback():
                pass

    @staticmethod
    def test__checks_store_items_for_rollback_failure_exception():
        action = StatefullAction()
        action.rollback_action(["input"], lambda state: 10)
        action._state = {}
        try:
            with action._checks_store_items_for_rollback():
                raise Exception()
        except Exception:
            pass
        assert action._state["action_failed"]

    @staticmethod
    def test__logging_do(monkeypatch):
        monkeypatch.setattr(StatefullAction, "get_name", MagicMock())
        send_info_mock = MagicMock()
        monkeypatch.setattr(InfoStreamer, "send_info", send_info_mock)
        action = StatefullAction()
        with action._logging_do():
            pass
        assert send_info_mock.call_count == 2

    @staticmethod
    def test__logging_do_exception(monkeypatch):
        monkeypatch.setattr(StatefullAction, "get_name", MagicMock())
        send_info_mock = MagicMock()
        monkeypatch.setattr(InfoStreamer, "send_info", send_info_mock)
        action = StatefullAction()
        try:
            with action._logging_do():
                raise Exception()
        except Exception:
            pass
        assert send_info_mock.call_count == 2

    @staticmethod
    def test__logging_undo(monkeypatch):
        monkeypatch.setattr(StatefullAction, "get_name", MagicMock())
        send_info_mock = MagicMock()
        monkeypatch.setattr(InfoStreamer, "send_info", send_info_mock)
        action = StatefullAction()
        with action._logging_undo():
            pass
        assert send_info_mock.call_count == 2

    @staticmethod
    def test__logging_undo_exception(monkeypatch):
        monkeypatch.setattr(StatefullAction, "get_name", MagicMock())
        send_info_mock = MagicMock()
        monkeypatch.setattr(InfoStreamer, "send_info", send_info_mock)
        action = StatefullAction()
        try:
            with action._logging_undo():
                raise Exception()
        except Exception:
            pass
        assert send_info_mock.call_count == 2

    @staticmethod
    def test_simulate(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        action = StatefullAction()
        action._state = ReferencesDict()
        state = {"a": 10}
        action.simulate("action", state)
        assert dict(action.state) == state

    @staticmethod
    def test_simulate_rollback(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        action = StatefullAction()
        action._state = ReferencesDict()
        after_state = {"a": 10}
        action.simulate("action", after_state)
        after_rollback_state = {"a": 0}
        action.simulate("rollback", after_rollback_state)
        assert dict(action.state) == after_rollback_state

    @staticmethod
    def test_get_prepared_action_no_action():
        action = StatefullAction()
        with pytest.raises(ActionException):
            action.get_prepared_action()

    @staticmethod
    def test_get_prepared_action(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        monkeypatch.setattr(StatefullAction, "_check_kwargs_for_action", MagicMock())
        monkeypatch.setattr(StatefullAction, "add_context_manager", MagicMock())
        action = StatefullAction(["input"], lambda state: state["input"])
        prepared = action.get_prepared_action(input=10)
        assert prepared.do() == 10

    @staticmethod
    def test_get_prepared_action_rollback(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        monkeypatch.setattr(StatefullAction, "_check_kwargs_for_action", MagicMock())
        monkeypatch.setattr(StatefullAction, "add_context_manager", MagicMock())
        action = StatefullAction(["input"], lambda state: 10)
        action.rollback_action(fct=lambda state: state["input"])
        prepared = action.get_prepared_action(input=20)
        assert prepared.undo() == 20


def test_statefull_action():
    @statefull_action(["input"])
    def fct_test(state):
        return state["input"]

    assert fct_test({"input": 10}) == 10


class TestUnitUnitAction(object):
    @staticmethod
    def test_init():
        assert UnitAction()

    @staticmethod
    def test_init_params():
        assert UnitAction(["test_item"], lambda state: 10)

    @staticmethod
    def test__enables_rollback():
        action = UnitAction()
        action._undo_hidden = lambda state: 10
        with action._enables_rollback():
            pass
        assert action.undo == action._undo_hidden

    @staticmethod
    def test_simulate(monkeypatch):
        _enables_rollback_mock = MagicMock()
        monkeypatch.setattr(UnitAction, "_enables_rollback", _enables_rollback_mock)
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        action = UnitAction()
        action._state = ReferencesDict()
        state = {"a": 10}
        action.simulate("action", state)
        assert _enables_rollback_mock.called

    @staticmethod
    def test_get_prepared_action_no_rollback():
        action = UnitAction(action_fct=lambda state: 10)
        with pytest.raises(ActionException):
            action.get_prepared_action()

    @staticmethod
    def test_get_prepared_action(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        monkeypatch.setattr(StatefullAction, "get_prepared_action", MagicMock)
        monkeypatch.setattr(StatefullAction, "add_context_manager", MagicMock())
        action = UnitAction(action_fct=lambda state: 10)
        action.rollback_action(fct=lambda state: 10)
        assert action.get_prepared_action()


def test_unit_action():
    @unit_action(["input"])
    def fct_test(state):
        state["input2"] = state["input"] + 10
        return state["input"]

    @fct_test.rollback_action(["input2"])
    def roll_test(state):
        return state["input2"]

    assert fct_test({"input": 10}) == 10


@pytest.fixture()
def complex_actions():
    results = []

    @statefull_action(state_items=["text"])
    def my_action(state):
        text = state["text"]
        state["before_text"] = text[::-1]
        results.append(text)
        state["id"] = 1
        state["id2"] = 2

    @my_action.rollback_action(["before_text", "id"])
    def my_action_rollback(state):
        results.append(state["id"])
        results.append(state["before_text"])

    @unit_action(["id"])
    def my_action_2(state):
        results.append(state["id"])

    @my_action_2.rollback_action([])
    def my_action_2_rollback(state):
        my_action_2(state)

    @my_action_2.rollback_context_manager
    @contextmanager
    def say_hello(action):
        results.append("Hello")
        yield

    return my_action, my_action_2, results


def test_actions(complex_actions):
    my_action, my_action_2, results = complex_actions
    prep_action = my_action.get_prepared_action(text="YOLO")
    prep_action_2 = my_action_2.get_prepared_action(id=prep_action.state.ref_to("id2"))
    prep_action_3 = my_action_2.get_prepared_action(id=prep_action.state.ref_to("id2"))
    prep_action.do()
    prep_action_2.do()
    prep_action_2.undo()
    prep_action.undo()
    prep_action_3.undo()  # Should do nothing.
    prep_action_3.do()
    assert results == [
        # prep_action.do()
        "YOLO",
        # prep_action_2.do()
        2,
        # prep_action_2.undo()
        "Hello", 2,
        # prep_action.undo()
        1,
        "OLOY",
        # prep_action_3.do()
        2
    ]


class SharedResultAction(object):
    def __init__(self):
        self.result = ""

    def gen_action(self, text):
        def action_fct():
            self.result += text
        if sys.version_info < (3, 0):
            action_fct = InstanceMethod(action_fct)
        action_fct._class = text  # necessary to differentiate the name of the different functions.
        return action_fct


class TestUnitActionsPipeline(object):
    @staticmethod
    def test_init():
        assert ActionsPipeline()

    @staticmethod
    def test_append_bad():
        with pytest.raises(ActionException):
            ActionsPipeline().append(object())

    @staticmethod
    def test_actions():
        assert not ActionsPipeline().actions

    @staticmethod
    def test_actions_read_only():
        with pytest.raises(ActionException):
            ActionsPipeline().actions = []

    @staticmethod
    def test_append(monkeypatch):
        monkeypatch.setattr(Action, "set_info_streamer", MagicMock())
        ap = ActionsPipeline()
        action = Action()
        ap.append(action)
        assert ap.actions[0] == action

    @staticmethod
    def test_append_in_order(monkeypatch):
        monkeypatch.setattr(Action, "set_info_streamer", MagicMock())
        ap = ActionsPipeline()
        action1 = Action()
        action2 = Action()
        ap.append(action1)
        ap.append(action2)
        assert ap.actions == [action1, action2]

    @staticmethod
    def test_set_info_streamer(monkeypatch):
        ap = ActionsPipeline()
        action1 = Action()
        action2 = Action()
        ap.append(action1)
        ap.append(action2)
        set_mock_1 = MagicMock()
        set_mock_2 = MagicMock()
        monkeypatch.setattr(action1, "set_info_streamer", set_mock_1)
        monkeypatch.setattr(action2, "set_info_streamer", set_mock_2)
        ap.set_info_streamer(InfoStreamer())
        assert set_mock_1.called and set_mock_2.called

    @staticmethod
    def test__action():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"))
        action2 = Action(shared_result.gen_action("b"))
        ap.append(action1)
        ap.append(action2)
        ap.do()
        assert shared_result.result == "ab"

    @staticmethod
    def test_actions_are_accessible():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"))
        action2 = Action(shared_result.gen_action("b"))
        ap.append(action1)
        ap.append(action2)
        assert ap.actions[1]  # This should have no impact.
        ap.do()
        assert shared_result.result == "ab"

    @staticmethod
    def test__rollback_action():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        action2 = Action(shared_result.gen_action("b"), shared_result.gen_action("d"))
        ap.append(action1)
        ap.append(action2)
        ap.do()
        ap.undo()
        assert shared_result.result == "abdc"

    @staticmethod
    def test__rollback_action_partial():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        action2 = Action(MagicMock(side_effect=Exception()), shared_result.gen_action("d"))
        ap.append(action1)
        ap.append(action2)
        try:
            ap.do()
        except Exception:
            pass
        ap.undo()
        assert shared_result.result == "adc"

    @staticmethod
    def test_simulate_until():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        action2 = Action(shared_result.gen_action("b"), shared_result.gen_action("d"))
        ap.append(action1)
        ap.append(action2)
        action1_name = action1.get_name("action")
        ap.simulate_until([(action1_name, {})])
        ap.do()
        ap.undo()
        assert shared_result.result == "bdc"

    @staticmethod
    def test_simulate_until_with_rollback():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        action2 = Action(shared_result.gen_action("b"), shared_result.gen_action("d"))
        ap.append(action1)
        ap.append(action2)
        action1_name = action1.get_name("action")
        action2_name = action2.get_name("action")
        action2_rollback_name = action2.get_name("rollback")
        ap.simulate_until([(action1_name, {}), (action2_name, {}), (action2_rollback_name, {})])
        ap.undo()
        assert shared_result.result == "c"

    @staticmethod
    def test_simulate_until_error():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        ap.append(action1)
        with pytest.raises(ActionException):
            ap.simulate_until([('garbage', {})])

    @staticmethod
    def test_simulate_until_partial():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        action2 = Action(shared_result.gen_action("b"), shared_result.gen_action("d"))
        ap.append(action1)
        ap.append(action2)
        # Mandatory to redefine names unless they all have the same name and simulate can't work fine.
        action1.set_name("action", "action1")
        action1.set_name("rollback", "rollback1")
        ap.simulate_until([("action1", {}), ("rollback1", {})])
        ap.undo()
        assert shared_result.result == ""

    @staticmethod
    def test_copy():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        ap.append(action1)
        ap2 = copy(ap)
        ap.do()
        ap2.do()
        assert shared_result.result == "aa"


@pytest.fixture()
def complex_pipeline(complex_actions):
    my_action, my_action_2, results = complex_actions
    prep_action = my_action.get_prepared_action(text="WOLOLOO")
    prep_action_2 = my_action_2.get_prepared_action(id=prep_action.state.ref_to("id2"))
    ap = ActionsPipeline()
    ap.append(prep_action)
    ap.append(prep_action_2)
    if sys.version_info < (3, 0):
        actions_names = ["tests.test_actions.my_action", "tests.test_actions.my_action_2",
                         "tests.test_actions.my_action_2_rollback", "tests.test_actions.my_action_rollback"]
    else:
        actions_names = ["tests.test_actions.complex_actions.my_action",
                         "tests.test_actions.complex_actions.my_action_2",
                         "tests.test_actions.complex_actions.my_action_2_rollback",
                         "tests.test_actions.complex_actions.my_action_rollback"]
    return ap, results, actions_names


def test_actions_pipeline(complex_pipeline):
    ap, results, _ = complex_pipeline
    ap.do()
    ap.undo()
    assert results == [
        # prep_action.do()
        "WOLOLOO",
        # prep_action_2.do()
        2,
        # prep_action_2.undo()
        "Hello", 2,
        # prep_action.undo()
        1,
        "OOLOLOW",
    ]


def test_actions_pipeline_simulate(complex_pipeline):
    ap, results, actions = complex_pipeline

    ap.simulate_until([
        (actions[0], {"text": "WOLOLOO", "id": 1, "id2": 2, "before_text": "OOLOLOW"}),
    ])
    ap.do()
    ap.undo()
    assert results == [2, "Hello", 2, 1, "OOLOLOW"]


def test_actions_pipeline_simulate_with_rollback(complex_pipeline):
    ap, results, actions = complex_pipeline
    ap.simulate_until([
        (actions[0], {"text": "WOLOLOO", "id": 1, "id2": 2, "before_text": "OOLOLOW"}),
        (actions[1], {"id": 3}),
        (actions[2], {"id": 2})
    ])
    ap.undo()
    assert results == [1, "OOLOLOW"]
