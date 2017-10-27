# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tools to customize feature and help in their writings.

"""
from inspect import currentframe

from ..abstracts import AbstractGetSetFactory
from ..utils import update_function_lineno


class constant(AbstractGetSetFactory):
    """Make a Feature return always the same value.

    This can only be used as a getter factory.

    Parameters
    ----------
    value :
        The value the Feature should return

    """

    def __init__(self, value):
        super(constant, self).__init__()
        self._value = value

    def build_getter(self):
        """Build a trivial function to return the constant value.

        """
        value = self._value

        def getter(self, driver):
            return value

        return getter

    def build_setter(self):
        """Return None as a constant is not settable.

        """
        return None  # pragma: no cover

LINENO_GET = currentframe().f_lineno


GET_DEF =\
"""
def get(self, driver):
    val = {}
    return {}

"""


LINENO_SET = currentframe().f_lineno

SET_DEF =\
"""
def set(self, driver, value):
    cmd = {}
    return driver.default_set_feature(self, cmd, value)
"""


class conditional(AbstractGetSetFactory):
    """Make a Feature modify getting/setting based on the driver state.

    Parameters
    ----------
    conditional_value : str
        String of the form 'a if driver.b else c'. When setting the value is
        accessible as value.

    default : bool
        Pass the result of the conditional evalutation to the
        default_get/set_feature method of the driver if True, otherwise
        directly return the result.
        When building a setter this MUST be true.

    """

    def __init__(self, conditional_value, default=False):
        super(conditional, self).__init__()
        self._cond = conditional_value
        self._default = default

    def build_getter(self):
        """Build the getter.

        """
        if not self._default:
            get_def = GET_DEF.format(self._cond, 'val')

        else:
            get_def = GET_DEF.format(self._cond,
                                     'driver.default_get_feature(self, val)')

        loc = {}
        # Consider that this file is the source of the function
        code = compile(get_def, __file__, 'exec')
        exec(code, globals(), loc)
        func = loc['get']

        # Set the lineno to point to the string source.
        update_function_lineno(func, LINENO_GET + 3)

        return func

    def build_setter(self):
        """Build the setter.

        """
        if not self._default:
            raise ValueError('Can build a setter only if default is True')

        loc = {}
        # Consider that this file is the source of the function
        code = compile(SET_DEF.format(self._cond), __file__, 'exec')
        exec(code, globals(), loc)
        func = loc['set']

        # Set the lineno to point to the string source.
        update_function_lineno(func, LINENO_GET + 3)

        return func
