# -*- coding: utf-8 -*-

import pytest

from pysyphe.data_structs import ReferencesDict, ReversibleList


class TestReferencesDict(object):
    @staticmethod
    def test_init():
        assert ReferencesDict({"a": 10})

    @staticmethod
    def test_RefValue_init():
        refs_dict = ReferencesDict()
        assert ReferencesDict.RefValue(refs_dict, "a")

    @staticmethod
    def test_RefValue_call():
        refs_dict = ReferencesDict({"a": 10})
        ref_val = ReferencesDict.RefValue(refs_dict, "a")
        assert ref_val() == 10

    @staticmethod
    def test_ref_to():
        refs_dict = ReferencesDict({"a": 10})
        assert refs_dict.ref_to("a")

    @staticmethod
    def test_ref_to_before():
        refs_dict = ReferencesDict()
        assert refs_dict.ref_to("a")

    @staticmethod
    def test_get():
        refs_dict = ReferencesDict({"a": 10})
        assert refs_dict["a"] == 10

    @staticmethod
    def test_get_ref():
        refs_dict = ReferencesDict({"a": 10})
        refs_dict2 = ReferencesDict({"b": refs_dict.ref_to("a")})
        assert refs_dict2["b"] == 10

    @staticmethod
    def test_get_missing():
        with pytest.raises(KeyError):
            refs_dict = ReferencesDict()
            refs_dict["a"]

    @staticmethod
    def test_get_ref_missing():
        with pytest.raises(KeyError):
            refs_dict = ReferencesDict()
            refs_dict2 = ReferencesDict({"a": refs_dict.ref_to("a")})
            refs_dict2["a"]

    @staticmethod
    def test_del():
        refs_dict = ReferencesDict({"a": 10})
        del refs_dict["a"]
        assert "a" not in refs_dict

    @staticmethod
    def test_iter():
        assert next(iter(ReferencesDict({"a": 10}))) == "a"

    @staticmethod
    def test_len():
        assert len(ReferencesDict({"a": 10})) == 1

    @staticmethod
    def test_str():
        assert str(ReferencesDict({"a": 10}))

    @staticmethod
    def test_repr():
        assert repr(ReferencesDict({"a": 10}))

    @staticmethod
    def test_ref_keys():
        refs_dict = ReferencesDict({"a": 10})
        refs_dict2 = ReferencesDict({"b": 20, "c": refs_dict.ref_to("a")})
        assert refs_dict2.ref_keys() == ["c"]

    @staticmethod
    def test_3_level():
        r1 = ReferencesDict()
        r2 = ReferencesDict()
        r3 = ReferencesDict()
        r1["a"] = 10
        r2["a"] = r1.ref_to("a")
        r3["a"] = r2.ref_to("a")
        r1["a"] = 20
        assert r3["a"] == 20


class TestReversibleList(object):
    @staticmethod
    def test_init():
        assert ReversibleList([1, 2, 3])

    @staticmethod
    def test_reverse():
        ReversibleList([1, 2, 3]).reverse()

    @staticmethod
    def test_append():
        ReversibleList([1, 2, 3]).append(4)

    @staticmethod
    def test_next():
        assert next(ReversibleList([1, 2, 3])) == 1

    @staticmethod
    def test_next_continuous():
        r = ReversibleList([1], continuous=True)
        next(r)
        assert next(r) == 1

    @staticmethod
    def test_len():
        assert len(ReversibleList([1, 2, 3])) == 3

    @staticmethod
    def test_bool():
        assert ReversibleList([1, 2, 3])

    @staticmethod
    def test_str():
        assert str(ReversibleList([1, 2, 3]))

    @staticmethod
    def test_reverse_behaviour():
        r = ReversibleList([1, 2, 3])
        for _ in r:
            pass
        r.reverse()
        assert [e for e in r] == [3, 2, 1]
