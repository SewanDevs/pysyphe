# -*- coding: utf-8 -*-

import pytest
from mock import MagicMock

from pysyphe.transactions import TransactionHandler, TransactionsManager
from pysyphe.exceptions import TransactionException, WeAreDoomedException


class TestTransactionsManager(object):
    @staticmethod
    def test_init():
        assert TransactionsManager()


    @staticmethod
    def test_add_transaction_handler():
        trm = TransactionsManager()
        trm.add_transaction_handler(TransactionHandler())


    @staticmethod
    def test_add_transaction_handler_begun():
        trm = TransactionsManager()
        with trm.begin():
            with pytest.raises(TransactionException):
                trm.add_transaction_handler(TransactionHandler())


    @staticmethod
    def test_begin(monkeypatch):
        trm = TransactionsManager()
        trh1 = TransactionHandler()
        trh2 = TransactionHandler()
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        fake_begin_1 = MagicMock()
        fake_begin_2 = MagicMock()
        monkeypatch.setattr(trh1, "begin", fake_begin_1)
        monkeypatch.setattr(trh2, "begin", fake_begin_2)
        with trm.begin():
            pass
        assert fake_begin_1.called
        assert fake_begin_2.called


    @staticmethod
    def test_execute(monkeypatch):
        trm = TransactionsManager()
        trh1 = TransactionHandler()
        trh2 = TransactionHandler()
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        fake_execute_1 = MagicMock()
        fake_execute_2 = MagicMock()
        monkeypatch.setattr(trh1, "execute", fake_execute_1)
        monkeypatch.setattr(trh2, "execute", fake_execute_2)
        with trm.begin():
            trm.execute()
        assert fake_execute_1.called
        assert fake_execute_2.called


    @staticmethod
    def test_execute_not_begun():
        trm = TransactionsManager()
        with pytest.raises(TransactionException):
            trm.execute()


    @staticmethod
    def test_rollback(monkeypatch):
        trm = TransactionsManager()
        trh1 = TransactionHandler()
        trh2 = TransactionHandler()
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        fake_rollback_1 = MagicMock()
        fake_rollback_2 = MagicMock()
        monkeypatch.setattr(trh1, "rollback", fake_rollback_1)
        monkeypatch.setattr(trh2, "rollback", fake_rollback_2)
        with trm.begin():
            trm.rollback()
        assert fake_rollback_1.called
        assert fake_rollback_2.called


    @staticmethod
    def test_rollback_not_begun():
        trm = TransactionsManager()
        with pytest.raises(TransactionException):
            trm.rollback()


    @staticmethod
    def test_begin_exception(monkeypatch):
        trm = TransactionsManager()
        trh1 = TransactionHandler()
        trm.add_transaction_handler(trh1)
        fake_rollback = MagicMock()
        monkeypatch.setattr(trm, "rollback", fake_rollback)

        class TestException(Exception):
            pass
        with pytest.raises(TestException):
            with trm.begin():
                raise TestException("I KILL YOU !")
        assert fake_rollback.called


    @staticmethod
    def test_begin_exception_already_rollbacked(monkeypatch):
        trm = TransactionsManager()
        trh1 = TransactionHandler()
        trm.add_transaction_handler(trh1)
        with pytest.raises(WeAreDoomedException):
            with trm.begin():
                trm.rollback()
                raise Exception("I KILL YOU !")


    @staticmethod
    def test_begin_exception_exception_during_rollback(monkeypatch):
        trm = TransactionsManager()
        trh1 = TransactionHandler()
        trm.add_transaction_handler(trh1)
        monkeypatch.setattr(trm, "rollback", MagicMock(side_effect=Exception))
        with pytest.raises(WeAreDoomedException):
            with trm.begin():
                raise Exception("I KILL YOU !")


    @staticmethod
    def test_commit(monkeypatch):
        trm = TransactionsManager()
        trh1 = TransactionHandler()
        trh2 = TransactionHandler()
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        fake_can_prepare_commit_1 = MagicMock(return_value=True)
        fake_can_prepare_commit_2 = MagicMock(return_value=False)
        monkeypatch.setattr(trh1, "can_prepare_commit", fake_can_prepare_commit_1)
        monkeypatch.setattr(trh2, "can_prepare_commit", fake_can_prepare_commit_2)
        fake_prepare_commit_1 = MagicMock(return_value=True)
        monkeypatch.setattr(trh1, "prepare_commit", fake_prepare_commit_1)
        fake_commit_1 = MagicMock()
        fake_commit_2 = MagicMock()
        monkeypatch.setattr(trh1, "commit", fake_commit_1)
        monkeypatch.setattr(trh2, "commit", fake_commit_2)
        with trm.begin():
            trm.commit()
        assert fake_can_prepare_commit_1.called
        assert fake_can_prepare_commit_2.called
        assert fake_prepare_commit_1.called
        assert fake_commit_1.called
        assert fake_commit_2.called


    @staticmethod
    def test_commit_not_begun():
        trm = TransactionsManager()
        with pytest.raises(TransactionException):
            trm.commit()


    @staticmethod
    def test_commit_prepare_failed(monkeypatch):
        trm = TransactionsManager()
        trh1 = TransactionHandler()
        trh2 = TransactionHandler()
        trm.add_transaction_handler(trh1)
        trm.add_transaction_handler(trh2)
        fake_can_prepare_commit_1 = MagicMock(return_value=True)
        fake_can_prepare_commit_2 = MagicMock(return_value=False)
        monkeypatch.setattr(trh1, "can_prepare_commit", fake_can_prepare_commit_1)
        monkeypatch.setattr(trh2, "can_prepare_commit", fake_can_prepare_commit_2)
        fake_prepare_commit_1 = MagicMock(return_value=False)
        monkeypatch.setattr(trh1, "prepare_commit", fake_prepare_commit_1)
        fake_commit_1 = MagicMock()
        fake_commit_2 = MagicMock()
        monkeypatch.setattr(trh1, "commit", fake_commit_1)
        monkeypatch.setattr(trh2, "commit", fake_commit_2)
        rollback_mock = MagicMock()
        monkeypatch.setattr(trm, "rollback", rollback_mock)
        with trm.begin():
            trm.commit()
        assert fake_can_prepare_commit_1.called
        assert fake_can_prepare_commit_2.called
        assert fake_prepare_commit_1.called
        assert not fake_commit_1.called
        assert not fake_commit_2.called
        assert rollback_mock.called
