# -*- coding: utf-8 -*-
from contextlib import ExitStack, contextmanager


@contextmanager
def nested(*contexts):
    """
           Reimplementation of nested in python 3.
    """
    with ExitStack() as stack:
        for ctx in contexts:
            stack.enter_context(ctx)
        yield contexts
