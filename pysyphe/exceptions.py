# -*- coding: utf-8 -*-


class PysypheException(Exception):
    pass


class PysypheKeyError(PysypheException):
    """ Thrown when a key is missing in a ReferencesDict """
    pass


class ActionException(PysypheException):
    pass
