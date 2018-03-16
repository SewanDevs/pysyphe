# -*- coding: utf-8 -*-


class TransacslashException(Exception):
    pass


class TransacslashKeyError(TransacslashException):
    """ Thrown when a key is missing in a ReferencesDict """
    pass


class ActionException(TransacslashException):
    pass
