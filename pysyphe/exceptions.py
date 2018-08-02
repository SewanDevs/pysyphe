# -*- coding: utf-8 -*-


class PysypheException(Exception):
    pass


class ActionException(PysypheException):
    pass


class TransactionException(PysypheException):
    pass


class WeAreDoomedException(TransactionException):
    def __init__(self, msg, exceptions_tracebacks):
        self.exceptions_tracebacks = exceptions_tracebacks
        self.msg = msg

    def __str__(self):
        return "\n".join(
            [self.msg, "Exceptions encountered in order:"] + self.exceptions_tracebacks
        )
