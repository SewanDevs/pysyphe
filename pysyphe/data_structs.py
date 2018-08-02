# -*- coding: utf-8 -*-

"""
Available data structures:
    * ReferencesDict: a dict that holds references to other dicts.
    * ReversibleList: a list that maintain an internal reading position
"""

from copy import copy
from collections import Iterator, MutableMapping


# TODO: add an utility function to browse references dicts to be sure there is no loop.


class ReferencesDict(MutableMapping):
    """ Behave like a dict but some (key, value) are references to another ReferencesDict's (key, value).

    It helps to make links between dicts, usefull when you need up-to-date values.
    To do this, you need to define some keys of the ReferencesDict using another ReferencesDict.

    Examples:
        >>> s1 = ReferencesDict()
        >>> s2 = ReferencesDict()
        >>> s1["a"] = 10
        >>> s2["a"] = s1.ref_to("a")
        >>> print(s2["a"])
        10
        >>> s1["a"] = 20
        >>> print(s2["a"])
        20

    Note:
        If you change a value that was a reference before, you will loose the reference.
    """

    class RefValue(object):
        """ RefValue is a reference to another dict's value. Call the RefValue to have the up-to-date value."""

        def __init__(self, refs_dict, key):
            """ Contruct a value that references another dict's value.
            Args:
                refs_dict: the dict this object is a reference to.
                key: the key in refs_dict this object is a reference to.
            """
            self.refs_dict = refs_dict
            self.key = key

        def __call__(self):
            """ Returns the up-to-date value """
            return self.refs_dict[self.key]

    def __init__(self, dic=None):
        self._dict = copy(dic) or {}

    def ref_to(self, key):
        """ Get a reference to a key of this dict. See ReferencesDict.RefValue to see how to use it. """
        return ReferencesDict.RefValue(self, key)

    def __getitem__(self, key):
        value = self._dict[key]
        if isinstance(value, ReferencesDict.RefValue):
            value = value()
        return value

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __delitem__(self, key):
        self._dict.__delitem__(key)

    def __iter__(self):
        return iter(self._dict.keys())

    def __len__(self):
        return len(self._dict.keys())

    def __str__(self):
        return str(dict(self))

    def __repr__(self):
        return "ReferencesDict({})".format(str(self))

    def ref_keys(self):
        """ Return the list of keys that are refs"""
        return [
            key
            for key, value in self._dict.items()
            if isinstance(value, ReferencesDict.RefValue)
        ]


class ReversibleList(Iterator):
    """ A list that can be reversed to return elements already returned but in the opposite order.

    You can reverse many times to re-read the whole list several times.
    The list may be a classic iterator that throws StopIteration at the end or be continuous and automatically reverse at the end.

    Examples:
        >>> r = ReversibleList([1,2,3])
        >>> elems = iter(r)
        >>> next(elems)
        1
        >>> next(elems)
        2
        >>> next(elems)
        3
        >>> next(elems)
        StopIteration:
        >>> elems.reverse()
        >>> next(elems)
        3
        >>> next(elems)
        2
        >>> next(elems)
        1
        >>> next(elems)
        StopIteration:
    """

    def __init__(self, list_=None, continuous=False):
        """ Contruct a reversible list.
        Args:
            list_: copy constructor.
            continuous: to have a continuous list that never ends and never throws StopIteration.
        """
        self._list = list(list_ or [])
        self._list_iterator = iter(self._list)
        self._position = 0
        self._continuous = continuous

    def reverse(self):
        self._list = self._list[::-1]
        self._position = len(self._list) - self._position
        self._list_iterator = iter(self._list[self._position :])

    def append(self, elem):
        self._list.append(elem)

    def next(self):
        try:
            next_elem = next(self._list_iterator)
        except StopIteration:
            if not self._continuous:
                raise
            else:
                self.reverse()
                next_elem = next(self._list_iterator)

        self._position += 1
        return next_elem

    __next__ = next

    def __len__(self):
        return len(self._list)

    def __bool__(self):
        return bool(self._list)

    def __str__(self):
        return str(self._list) + " pos {}".format(self._position)

    def __copy__(self):
        other = ReversibleList(self._list, continuous=self._continuous)
        other._position = self._position
        return other
