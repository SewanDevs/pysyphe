# -*- coding: utf-8 -*-

from pysyphe.exceptions import (
    PysypheException,
    ActionException,
    TransactionException,
    WeAreDoomedException,
)


def test_PysypheException():
    assert PysypheException()


def test_ActionException():
    assert ActionException()


def test_TransactionException():
    assert TransactionException()


def test_WeAreDoomedException():
    exc = WeAreDoomedException("fail", ["traceback1", "traceback2"])
    assert str(exc)
