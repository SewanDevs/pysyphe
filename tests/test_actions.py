# -*- coding: utf-8 -*-

import sys
import pytest
from copy import copy
from contextlib import contextmanager
from mock import MagicMock

from pysyphe.actions import (
    Action,
    StatefullAction,
    statefull_action,
    UnitAction,
    unit_action,
    ActionsPipeline,
    _format_fct_name,
)
from pysyphe.actions import Actions, staticaction
from pysyphe.exceptions import ActionException
from pysyphe.streamers import InfoStreamer
from pysyphe.data_structs import ReferencesDict

if sys.version_info < (3, 0):
    from pysyphe.py2 import InstanceMethod


# TODO: write more tests for format_fct_name
def test__format_fct_name():
    def yolo():
        pass

    assert _format_fct_name(yolo)


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


class TestAction(object):
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
    @pytest.mark.parametrize("action_side", ["action", "rollback"])
    @pytest.mark.parametrize("step", ["begin", "end"])
    @pytest.mark.parametrize("kwargs", [None, {"extra": 10}])
    def test_notify(monkeypatch, action_side, step, kwargs):
        send_info_mock = MagicMock()
        monkeypatch.setattr(InfoStreamer, "send_info", send_info_mock)
        kwargs = kwargs or {}
        Action(lambda: 10, lambda: 10).notify(action_side, step, **kwargs)
        assert send_info_mock.called

    @staticmethod
    def test_do_nothing():
        with pytest.raises(ActionException):
            Action().do()

    @staticmethod
    def test_do(monkeypatch):
        monkeypatch.setattr(Action, "notify", MagicMock())
        assert Action(lambda: 10).do() == 10

    @staticmethod
    def test_undo_nothing():
        with pytest.raises(ActionException):
            Action().undo()

    @staticmethod
    def test_undo(monkeypatch):
        monkeypatch.setattr(Action, "notify", MagicMock())
        assert Action(lambda: 10, lambda: -10).undo() == -10

    @staticmethod
    def test_do_notify(monkeypatch):
        notif_mock = MagicMock()
        monkeypatch.setattr(Action, "notify", notif_mock)
        action = Action(MagicMock())
        action.do()
        assert notif_mock.call_count == 2

    @staticmethod
    def test_do_notify_exception(monkeypatch):
        notif_mock = MagicMock()
        monkeypatch.setattr(Action, "notify", notif_mock)
        action = Action(MagicMock(side_effect=Exception))
        try:
            action.do()
        except Exception:
            pass
        assert notif_mock.call_count == 2

    @staticmethod
    def test_undo_notify(monkeypatch):
        notif_mock = MagicMock()
        monkeypatch.setattr(Action, "notify", notif_mock)
        action = Action(None, MagicMock())
        action.undo()
        assert notif_mock.call_count == 2

    @staticmethod
    def test_undo_notify_exception(monkeypatch):
        notif_mock = MagicMock()
        monkeypatch.setattr(Action, "notify", notif_mock)
        action = Action(None, MagicMock(side_effect=Exception))
        try:
            action.undo()
        except Exception:
            pass
        assert notif_mock.call_count == 2

    @staticmethod
    @pytest.mark.parametrize(
        "action_type, function_to_call, result",
        [
            ("action", "do", "ba"),
            ("rollback", "do", ""),
            ("action", "undo", ""),
            ("rollback", "undo", "ba"),
        ],
    )
    def test_add_context_manager(action_type, function_to_call, result):
        ac = Action(lambda: 10, lambda: -10)
        csm = SharedContextManager()
        ac.add_context_manager(action_type, csm.gen_context_manager("b", "a"))
        getattr(ac, function_to_call)()
        assert csm.result == result

    @staticmethod
    @pytest.mark.parametrize(
        "action_type, function_to_call, result",
        [
            ("action", "do", "b2bb3a3aa2"),
            ("rollback", "do", ""),
            ("action", "undo", ""),
            ("rollback", "undo", "b2bb3a3aa2"),
        ],
    )
    def test_add_context_manager_inner(action_type, function_to_call, result):
        ac = Action(lambda: 10, lambda: -10)
        csm = SharedContextManager()
        ac.add_context_manager(action_type, csm.gen_context_manager("b", "a"))
        ac.add_context_manager(action_type, csm.gen_context_manager("b2", "a2"))
        ac.add_context_manager(
            action_type, csm.gen_context_manager("b3", "a3"), inner=True
        )
        getattr(ac, function_to_call)()
        assert csm.result == result

    @staticmethod
    def test_action_context_manager(monkeypatch):
        monkeypatch.setattr(Action, "add_context_manager", MagicMock())
        action = Action()
        assert action.action_context_manager(MagicMock())

    @staticmethod
    def test_rollback_context_manager(monkeypatch):
        monkeypatch.setattr(Action, "add_context_manager", MagicMock())
        action = Action()
        assert action.rollback_context_manager(MagicMock())

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
        a.add_context_manager("action", MagicMock())
        a.add_context_manager("rollback", MagicMock())
        assert copy(a)

    @staticmethod
    def test_simulate():
        Action(lambda: 10, lambda: -10).simulate()


class TestStateFullAction(object):
    @staticmethod
    def test_init():
        assert StatefullAction()

    @staticmethod
    def test_init_params():
        assert StatefullAction(["test_item"], lambda state: 10, name="better_name")

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
        monkeypatch.setattr(
            StatefullAction, "_check_fct", MagicMock(side_effect=ActionException)
        )
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
    def test_rollback_action_with_name(monkeypatch):
        monkeypatch.setattr(StatefullAction, "_check_fct", MagicMock())
        action = StatefullAction(name="better_name")
        decorator = action.rollback_action(name="better_rollback_name")
        decorator(lambda state: 10)
        assert action.rollback_name == "better_rollback_name"

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
    def test__checks_state_items_for_rollback():
        action = StatefullAction()
        action.rollback_action(["input"], lambda state: 10)
        action._state = {}
        with action._checks_state_items_for_rollback():
            action._state["input"] = 10

    @staticmethod
    def test__checks_state_items_for_rollback_failure_missing():
        action = StatefullAction()
        action.rollback_action(["input"], lambda state: 10)
        action._state = {}
        with pytest.raises(ActionException):
            with action._checks_state_items_for_rollback():
                pass

    @staticmethod
    def test__checks_state_items_for_rollback_failure_exception():
        action = StatefullAction()
        action.rollback_action(["input"], lambda state: 10)
        action._state = {}
        try:
            with action._checks_state_items_for_rollback():
                raise Exception()
        except Exception:
            pass
        assert action._state["action_failed"]

    @staticmethod
    def test_notify(monkeypatch):
        notify_mock = MagicMock()
        monkeypatch.setattr(Action, "notify", notify_mock)
        StatefullAction().notify("action", "begin")
        assert notify_mock.called

    @staticmethod
    def test_notify_no_rollback(monkeypatch):
        notify_mock = MagicMock()
        monkeypatch.setattr(Action, "notify", notify_mock)
        act = StatefullAction([], lambda state: 10)
        prep = act.get_prepared_action()
        prep.notify("rollback", "begin")
        assert not notify_mock.called

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
    def test_get_prepared_action_already_prepared(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        monkeypatch.setattr(StatefullAction, "_check_kwargs_for_action", MagicMock())
        monkeypatch.setattr(StatefullAction, "add_context_manager", MagicMock())
        action = StatefullAction(["input"], lambda state: state["input"])
        prepared = action.get_prepared_action(input=10)
        with pytest.raises(ActionException):
            prepared.get_prepared_action()

    @staticmethod
    def test_get_prepared_action_rollback(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        monkeypatch.setattr(StatefullAction, "_check_kwargs_for_action", MagicMock())
        monkeypatch.setattr(StatefullAction, "add_context_manager", MagicMock())
        action = StatefullAction(["input"], lambda state: 10)
        action.rollback_action(fct=lambda state: state["input"])
        prepared = action.get_prepared_action(input=20)
        assert prepared.undo() == 20

    @staticmethod
    def test_get_prepared_action_twice(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        monkeypatch.setattr(StatefullAction, "_check_kwargs_for_action", MagicMock())
        monkeypatch.setattr(StatefullAction, "add_context_manager", MagicMock())
        action = StatefullAction(["input"], lambda state: state["input"])
        prepared = action.get_prepared_action(input=20)
        prepared2 = action.get_prepared_action(input=30)
        assert prepared.do() == 20
        assert prepared2.do() == 30

    @staticmethod
    def test_get_prepared_action_change_name(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        monkeypatch.setattr(StatefullAction, "_check_kwargs_for_action", MagicMock())
        monkeypatch.setattr(StatefullAction, "add_context_manager", MagicMock())
        action = StatefullAction(["input"], lambda state: 10, name="base_name")
        prepared = action.get_prepared_action(input=20)
        prepared.name = "prepared_action_name"
        assert action.name == "base_name"
        assert prepared.name == "prepared_action_name"

    @staticmethod
    def test_get_prepared_action_add_context_manager(monkeypatch):
        monkeypatch.setattr(InfoStreamer, "send_info", MagicMock())
        monkeypatch.setattr(StatefullAction, "_check_kwargs_for_action", MagicMock())
        action = StatefullAction(["input"], lambda state: 10)
        prepared = action.get_prepared_action(input=20)
        context_manager_mock = MagicMock()
        prepared.add_context_manager("action", context_manager_mock)
        prepared2 = action.get_prepared_action(input=20)
        context_manager_mock2 = MagicMock()
        prepared2.add_context_manager("action", context_manager_mock2)
        prepared.do()
        assert context_manager_mock.called and not context_manager_mock2.called
        prepared2.do()
        assert context_manager_mock.call_count == 1 and context_manager_mock2.called


def test_statefull_action():
    @statefull_action(["input"], name="better_name")
    def fct_test(state):
        return state["input"]

    assert fct_test({"input": 10}) == 10
    assert fct_test.name == "better_name"


class TestUnitAction(object):
    @staticmethod
    def test_init():
        assert UnitAction()

    @staticmethod
    def test_init_params():
        assert UnitAction(["test_item"], lambda state: 10, name="better_name")

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
        "Hello",
        2,
        # prep_action.undo()
        1,
        "OLOY",
        # prep_action_3.do()
        2,
    ]


class SharedResultAction(object):
    def __init__(self):
        self.result = ""

    def gen_action(self, text):
        def action_fct():
            self.result += text

        if sys.version_info < (3, 0):
            action_fct = InstanceMethod(action_fct)
        action_fct._class = (
            text
        )  # necessary to differentiate the name of the different functions.
        return action_fct


class TestActionsPipeline(object):
    @staticmethod
    def test_init():
        assert ActionsPipeline(name="pipeline_name")

    @staticmethod
    def test_init_with_list():
        action = Action()
        action2 = Action()
        ap = ActionsPipeline([action, action2])
        assert ap.actions[0] == action and ap.actions[1] == action2

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
        action2 = Action(
            MagicMock(side_effect=Exception()), shared_result.gen_action("d")
        )
        ap.append(action1)
        ap.append(action2)
        try:
            ap.do()
        except Exception:
            pass
        ap.undo()
        assert shared_result.result == "adc"

    @staticmethod
    def test_notify_no_name(monkeypatch):
        notify_mock = MagicMock()
        monkeypatch.setattr(Action, "notify", notify_mock)
        ActionsPipeline().notify()
        assert not notify_mock.called

    @staticmethod
    def test_notify(monkeypatch):
        notify_mock = MagicMock()
        monkeypatch.setattr(Action, "notify", notify_mock)
        ActionsPipeline(name="pipeline").notify()
        assert notify_mock.called

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
        ap.simulate_until(
            [(action1_name, {}), (action2_name, {}), (action2_rollback_name, {})]
        )
        ap.undo()
        assert shared_result.result == "c"

    @staticmethod
    def test_simulate_until_error():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        ap.append(action1)
        with pytest.raises(ActionException):
            ap.simulate_until([("garbage", {})])

    @staticmethod
    def test_simulate_until_error_undo():
        ap = ActionsPipeline()
        shared_result = SharedResultAction()
        action1 = Action(shared_result.gen_action("a"), shared_result.gen_action("c"))
        ap.append(action1)
        action1_name = action1.get_name("action")
        with pytest.raises(ActionException):
            ap.simulate_until([(action1_name, {}), ("garbage", {})])

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
        actions_names = [
            "tests.test_actions.my_action",
            "tests.test_actions.my_action_2",
            "tests.test_actions.my_action_2_rollback",
            "tests.test_actions.my_action_rollback",
        ]
    else:
        actions_names = [
            "tests.test_actions.complex_actions.my_action",
            "tests.test_actions.complex_actions.my_action_2",
            "tests.test_actions.complex_actions.my_action_2_rollback",
            "tests.test_actions.complex_actions.my_action_rollback",
        ]
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
        "Hello",
        2,
        # prep_action.undo()
        1,
        "OOLOLOW",
    ]


def test_actions_pipeline_simulate(complex_pipeline):
    ap, results, actions = complex_pipeline

    ap.simulate_until(
        [(actions[0], {"text": "WOLOLOO", "id": 1, "id2": 2, "before_text": "OOLOLOW"})]
    )
    ap.do()
    ap.undo()
    assert results == [2, "Hello", 2, 1, "OOLOLOW"]


def test_actions_pipeline_simulate_with_rollback(complex_pipeline):
    ap, results, actions = complex_pipeline
    ap.simulate_until(
        [
            (
                actions[0],
                {"text": "WOLOLOO", "id": 1, "id2": 2, "before_text": "OOLOLOW"},
            ),
            (actions[1], {"id": 3}),
            (actions[2], {"id": 2}),
        ]
    )
    ap.undo()
    assert results == [1, "OOLOLOW"]


class TestActions(object):
    class FakeActions(Actions):
        @staticaction
        @statefull_action(["item"])
        def fake_action(state):
            return state["item"]

        @staticaction
        @fake_action.rollback_action(["item"])
        def fake_rollback(state):
            return state["item"]

    @staticmethod
    def test_Actions_direct_call_action():
        assert TestActions.FakeActions().fake_action({"item": 10}) == 10

    @staticmethod
    def test_Actions_direct_call_rollback():
        assert TestActions.FakeActions().fake_rollback({"item": 10}) == 10

    @staticmethod
    def test_Actions_prepare():
        assert TestActions.FakeActions().fake_action.get_prepared_action(item=10)

    @staticmethod
    def test_Actions_name():
        # Check name of class is inside the action name
        assert "FakeActions" in TestActions.FakeActions().fake_action.name


def test_classic_context_manager():
    # Purpose of this test is to check that classic context manager works too
    action = Action(action_fct=lambda: 10)

    @action.action_context_manager
    class ContextManager(object):
        def __init__(self, action):
            self.action = action

        def __enter__(self):
            # May use self.action
            pass

        def __exit__(self, *args, **kwargs):
            # May use self.action
            pass

    ContextManager.__enter__ = MagicMock()
    ContextManager.__exit__ = MagicMock()
    action.do()
    assert ContextManager.__enter__.called
    assert ContextManager.__exit__.called


def test_info_streaming():
    @statefull_action(["item"])
    def fake_action(state):
        state["other"] = state["item"] + 5
        pass

    @fake_action.rollback_action(["other"])
    def fake_rollback(state):
        state["last"] = state["other"] + 5
        pass

    prep1 = fake_action.get_prepared_action(item=10)
    prep1.name = "action1"
    prep1.rollback_name = "rollback1"
    prep2 = fake_action.get_prepared_action(item=100)
    prep2.name = "action2"
    prep2.rollback_name = "rollback2"

    ap = ActionsPipeline()
    ap.append(prep1)
    ap.append(prep2)
    ap.name = "pipeline"
    ap.rollback_name = "pipeline_rollback"

    streamed_info = []

    class FakeInfoStreamer(InfoStreamer):
        def send_info(self, **kwargs):
            if "begin" in kwargs:
                step_type = "begin"
            if "end" in kwargs:
                step_type = "end"
            if "state" in kwargs:
                info = (kwargs["action_name"], step_type, dict(kwargs["state"]))
            else:
                info = (kwargs["action_name"], step_type)
            streamed_info.append(info)

    ap.set_info_streamer(FakeInfoStreamer())
    ap.do()
    ap.undo()

    assert streamed_info == [
        ("pipeline", "begin"),
        ("action1", "begin", {"item": 10}),
        ("action1", "end", {"item": 10, "other": 15}),
        ("action2", "begin", {"item": 100}),
        ("action2", "end", {"item": 100, "other": 105}),
        ("pipeline", "end"),
        ("pipeline_rollback", "begin"),
        ("rollback2", "begin", {"item": 100, "other": 105}),
        ("rollback2", "end", {"item": 100, "other": 105, "last": 110}),
        ("rollback1", "begin", {"item": 10, "other": 15}),
        ("rollback1", "end", {"item": 10, "other": 15, "last": 20}),
        ("pipeline_rollback", "end"),
    ]


def test_context_manager_retry():
    mock_action = MagicMock(side_effect=Exception)
    action = Action(mock_action)

    @action.action_context_manager
    @contextmanager
    def retry_do_3_times_if_it_fails(action):
        try:
            yield
        except Exception:
            action.retries = getattr(action, "retries", 0) + 1
            if action.retries < 3:
                action.do()
            else:
                raise

    with pytest.raises(Exception):
        action.do()

    assert mock_action.call_count == 3
