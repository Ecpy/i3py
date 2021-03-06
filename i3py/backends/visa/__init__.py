# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base classes for instruments relying on the VISA communication protocol.

"""
try:
    from pyvisa import constants
    from pyvisa import errors
except ImportError as e:
    msg = 'The PyVISA library is necessary to use the visa backend.'
    raise ImportError(msg) from e
else:
    from .message_based import VisaMessageDriver
    from .registry_based import VisaRegistryDriver
    from .base import (BaseVisaDriver, get_visa_resource_manager,
                       set_visa_resource_manager)

    __all__ = ['constants', 'errors',
               'BaseVisaDriver', 'VisaMessageDriver', 'VisaRegistryDriver',
               'get_visa_resource_manager', 'set_visa_resource_manager']
