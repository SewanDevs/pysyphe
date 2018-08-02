# -*- coding: utf-8 -*-

import pytest
from mock import MagicMock

from pysyphe.streamers import (
    InfoStreamer,
    HumanReadableActionsLogger,
    ActionsLoggerForSimulation,
)


def test_InfoStreamer():
    assert InfoStreamer()


@pytest.mark.parametrize(
    "send_info_kwargs",
    [
        {"action_name": "name", "state": {"value": 10}, "begin": True},
        {"action_name": "name", "state": {"value": 10}, "end": True},
        {
            "action_name": "name",
            "state": {"value": 10},
            "end": True,
            "exc": Exception(),
        },
        {
            "action_name": "rollback_name",
            "state": {"value": 10},
            "begin": True,
            "rollback_of": "name",
        },
        {"action_name": "name", "state": {"value": 10}, "simul": True},
    ],
)
def test_HumanReadableActionsLogger(monkeypatch, send_info_kwargs):
    log_mock = MagicMock()
    monkeypatch.setattr("pysyphe.streamers.logger.info", log_mock)
    monkeypatch.setattr("traceback.format_exc", MagicMock(return_value=""))
    streamer = HumanReadableActionsLogger()
    streamer.send_info(**send_info_kwargs)
    assert log_mock.called


@pytest.mark.xfail
@pytest.mark.parametrize(
    "send_info_kwargs",
    [
        {"action_name": "name", "state": {"value": 10}, "begin": True},
        {"action_name": "name", "state": {"value": 10}, "end": True},
        {
            "action_name": "name",
            "state": {"value": 10},
            "end": True,
            "exc": Exception(),
        },
        {
            "action_name": "rollback_name",
            "state": {"value": 10},
            "begin": True,
            "rollback_of": "name",
        },
        {"action_name": "name", "state": {"value": 10}, "simul": True},
    ],
)
def test_ActionsLoggerForSimulation(monkeypatch, send_info_kwargs):
    log_mock = MagicMock()
    monkeypatch.setattr("pysyphe.streamers.logger.info", log_mock)
    monkeypatch.setattr("traceback.format_exc", MagicMock(return_value=""))
    streamer = ActionsLoggerForSimulation()
    streamer.send_info(**send_info_kwargs)
    assert log_mock.called
