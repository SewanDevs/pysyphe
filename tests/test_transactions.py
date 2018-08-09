# -*- coding: utf-8 -*-

import pytest
from mock import MagicMock

from pysyphe.transactions import (
    TransactionHandler,
    TransactionsManager,
    PipelineTransactionHandler,
)
from pysyphe.exceptions import TransactionException, WeAreDoomedException


def test_TransactionHandler():
    th = TransactionHandler()
    th.begin()
    th.execute()
    th.can_prepare_commit()
    th.rollback()
    th.prepare_commit()
    th.commit()


class TransactionHandlerMock(TransactionHandler):
    def __init__(self, mocks=None):
        mocks = mocks or {}
        self.begin = mocks.get("begin") or MagicMock()
        self.execute = mocks.get("execute") or MagicMock()
        self.rollback = mocks.get("rollback") or MagicMock()
        self.can_prepare_commit = mocks.get("can_prepare_commit") or MagicMock()
        self.prepare_commit = mocks.get("prepare_commit") or MagicMock()
        self.commit = mocks.get("commit") or MagicMock()


class TestTransactionsManager(object):
    @staticmethod
    def test_init():
        assert TransactionsManager()

    @staticmethod
    def test_add_transaction_handler():
        trm = TransactionsManager()
        th = TransactionHandlerMock()
        trm.add_transaction_handler(th)
        assert th in trm._transaction_handlers

    @staticmethod
    def test_add_transaction_handler_begun():
        trm = TransactionsManager()
        with trm.begin():
            with pytest.raises(TransactionException):
                trm.add_transaction_handler(TransactionHandlerMock())

    @staticmethod
    def test__add_exception_encoutered():
        trm = TransactionsManager()
        try:
            raise Exception()
        except Exception as e:
            trm._add_exception_encoutered(e)
        assert len(trm.exceptions_encountered) == 1

    @staticmethod
    def test__add_exception_encoutered_no_duplicates():
        trm = TransactionsManager()
        try:
            try:
                raise Exception()
            except Exception as e:
                trm._add_exception_encoutered(e)
        except Exception as e:
            trm._add_exception_encoutered(e)
        assert len(trm.exceptions_encountered) == 1

    @staticmethod
    def test__add_exception_encoutered_no_missing():
        trm = TransactionsManager()
        try:
            raise Exception()
        except Exception as e:
            trm._add_exception_encoutered(e)
        try:
            raise Exception()
        except Exception as e:
            trm._add_exception_encoutered(e)
        assert len(trm.exceptions_encountered) == 2

    @staticmethod
    def test_begin():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock()
        trh2 = TransactionHandlerMock()
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        with trm.begin():
            pass
        assert trh1.begin.called
        assert trh2.begin.called

    @staticmethod
    def test_execute():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock()
        trh2 = TransactionHandlerMock()
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        with trm.begin():
            trm.execute()
        assert trh1.execute.called
        assert trh2.execute.called

    @staticmethod
    def test_execute_not_begun():
        trm = TransactionsManager()
        with pytest.raises(TransactionException):
            trm.execute()

    @staticmethod
    def test_rollback():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock()
        trh2 = TransactionHandlerMock()
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        with trm.begin():
            trm.rollback()
        assert trh1.rollback.called
        assert trh2.rollback.called

    @staticmethod
    def test_rollback_not_begun():
        trm = TransactionsManager()
        with pytest.raises(TransactionException):
            trm.rollback()

    @staticmethod
    def test_rollback_exceptions():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock({"rollback": MagicMock(side_effect=Exception)})
        trh2 = TransactionHandlerMock({"rollback": MagicMock(side_effect=Exception)})
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        with pytest.raises(Exception):
            with trm.begin():
                trm.rollback()
        assert trh1.rollback.called
        assert trh2.rollback.called
        assert len(trm.exceptions_encountered) == 2

    @staticmethod
    def test_begin_exception():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock()
        trm.add_transaction_handler(trh1)

        class TestException(Exception):
            pass

        with pytest.raises(TestException):
            with trm.begin():
                raise TestException("I KILL YOU !")
        assert trh1.rollback.called

    @staticmethod
    def test_begin_exception_already_rollbacked():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock()
        trm.add_transaction_handler(trh1)
        with pytest.raises(WeAreDoomedException):
            with trm.begin():
                trm.rollback()
                raise Exception("I KILL YOU !")

    @staticmethod
    def test_begin_exception_exception_during_rollback():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock({"rollback": MagicMock(side_effect=Exception)})
        trm.add_transaction_handler(trh1)
        with pytest.raises(WeAreDoomedException):
            with trm.begin():
                raise Exception("I KILL YOU !")
        assert len(trm.exceptions_encountered) == 2

    @staticmethod
    def test_commit():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock(
            {
                "can_prepare_commit": MagicMock(return_value=True),
                "prepare_commit": MagicMock(return_value=True),
            }
        )
        trh2 = TransactionHandlerMock(
            {"can_prepare_commit": MagicMock(return_value=False)}
        )
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        with trm.begin():
            trm.commit()
        assert trh1.can_prepare_commit.called
        assert trh2.can_prepare_commit.called
        assert trh1.prepare_commit.called
        assert trh1.commit.called
        assert trh2.commit.called

    @staticmethod
    def test_commit_not_begun():
        trm = TransactionsManager()
        with pytest.raises(TransactionException):
            trm.commit()

    @staticmethod
    def test_commit_prepare_failed():
        trm = TransactionsManager()
        trh1 = TransactionHandlerMock(
            {
                "can_prepare_commit": MagicMock(return_value=True),
                "prepare_commit": MagicMock(return_value=False),
            }
        )
        trh2 = TransactionHandlerMock(
            {"can_prepare_commit": MagicMock(return_value=False)}
        )
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        trm.rollback = MagicMock()
        with trm.begin():
            trm.commit()
        assert trh1.can_prepare_commit.called
        assert trh2.can_prepare_commit.called
        assert trh1.prepare_commit.called
        assert not trh1.commit.called
        assert not trh2.commit.called
        assert trm.rollback.called

    @staticmethod
    def test_add_mutex_handler():
        trm = TransactionsManager()
        th = TransactionHandlerMock()
        trm.set_mutex_handler(th)
        assert trm._mutex_handler == th

    @staticmethod
    def test_add_mutex_handler_begun():
        trm = TransactionsManager()
        with trm.begin():
            with pytest.raises(TransactionException):
                trm.set_mutex_handler(TransactionHandlerMock())

    @staticmethod
    def test_mutex_handler_begin_first():
        trm = TransactionsManager()
        begins = []
        mh = TransactionHandlerMock({"begin": lambda: begins.append("A")})
        th = TransactionHandlerMock({"begin": lambda: begins.append("B")})
        trm.set_mutex_handler(mh)
        trm.add_transaction_handler(th)
        with trm.begin():
            assert begins == ["A", "B"]

    @staticmethod
    def test_mutex_handler_commit_last():
        trm = TransactionsManager()
        commits = []
        mh = TransactionHandlerMock({"commit": lambda: commits.append("A")})
        th = TransactionHandlerMock({"commit": lambda: commits.append("B")})
        trm.set_mutex_handler(mh)
        trm.add_transaction_handler(th)
        with trm.begin():
            trm.commit()
            assert commits == ["B", "A"]

    @staticmethod
    def test_mutex_handler_rollback_last():
        trm = TransactionsManager()
        rollbacks = []
        mh = TransactionHandlerMock({"rollback": lambda: rollbacks.append("A")})
        th = TransactionHandlerMock({"rollback": lambda: rollbacks.append("B")})
        trm.set_mutex_handler(mh)
        trm.add_transaction_handler(th)
        with trm.begin():
            trm.rollback()
            assert rollbacks == ["B", "A"]

    @staticmethod
    def test_mutex_handler_begin_exception():
        trm = TransactionsManager()
        begins = []
        mh = TransactionHandlerMock({"begin": lambda: begins.append("A")})
        th = TransactionHandlerMock({"begin": MagicMock(side_effect=Exception())})
        trm.set_mutex_handler(mh)
        trm.add_transaction_handler(th)
        try:
            with trm.begin():
                pass
        except Exception:
            pass
        assert begins == ["A"]


class ActionsPipelineMock(object):
    def __init__(self, name=None):
        self.do = MagicMock()
        self.undo = MagicMock()
        self.name = name


class TestPipelineTransactionHandler(object):
    @staticmethod
    def test_init():
        assert PipelineTransactionHandler(ActionsPipelineMock())

    @staticmethod
    def test_actions_pipeline():
        pth = PipelineTransactionHandler()
        pipeline = ActionsPipelineMock()
        pth.actions_pipeline = pipeline
        assert pth.actions_pipeline == pipeline

    @staticmethod
    def test_pipeline_name():
        pth = PipelineTransactionHandler(ActionsPipelineMock("pipeline_name"))
        assert pth.pipeline_name == "pipeline_name"

    @staticmethod
    def test_pipeline_name_setter():
        pth = PipelineTransactionHandler()
        with pytest.raises(TransactionException):
            pth.pipeline_name = "pipeline_name"

    @staticmethod
    def test_can_prepare_commit():
        pth = PipelineTransactionHandler()
        assert pth.can_prepare_commit()

    @staticmethod
    def test_prepare_commit():
        pth = PipelineTransactionHandler()
        assert pth.prepare_commit()

    @staticmethod
    def test_execute():
        pipeline = ActionsPipelineMock()
        pth = PipelineTransactionHandler(pipeline)
        pth.execute()
        assert pipeline.do.called
        assert not pipeline.undo.called

    @staticmethod
    def test_execute_no_pipeline():
        pth = PipelineTransactionHandler()
        with pytest.raises(TransactionException):
            pth.execute()

    @staticmethod
    def test_rollback():
        pipeline = ActionsPipelineMock()
        pth = PipelineTransactionHandler(pipeline)
        pth.rollback()
        assert not pipeline.do.called
        assert pipeline.undo.called

    @staticmethod
    def test_rollback_no_pipeline():
        pth = PipelineTransactionHandler()
        with pytest.raises(TransactionException):
            pth.rollback()
