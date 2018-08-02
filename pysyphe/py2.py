# -*- coding: utf-8 -*-

"""
    Bad re-implementations mandatory in py2 for the mecanism to work.
"""


class InstanceMethod(object):
    """ A bad re-implementation of instancemethod because in python2 you can't have custom attributes on instancemethod.
        Useless in python3 """

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class StaticMethod(object):
    """ A re-implementation of staticmethod because in python2 you can't have custom attributes on staticmethod.
        Useless in python3 """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        return self.func
