# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""This file is meant to check the working of the driver for the BE2101.

The rack is expected to have a BE2101 in one slot, whose output can be safely
switched on and off and whose output value can vary (and has a large impedance)

"""
# Visa connection info
VISA_RESOURCE_NAME = 'TCPIP::192.168.0.10::5025::SOCKET'

# Index of the slot in which the BE2101 can be found (starting from 1)
MODULE_INDEX = 1

from i3py.drivers.itest import BN100

with BN100(VISA_RESOURCE_NAME) as rack:

    # Test reading all features
    print('Available modules', rack.be2141.available)

    module = rack.be2141[MODULE_INDEX]
    print('Manufacturer', module.identity.manufacturer)
    print('Model', module.identity.model)
    print('Serial number', module.identity.serial)
    print('Firmware', module.identity.firmware)

    print('Testing output')
    output = module.output[1]
    for f_name in output.__feats__:
        print('    ', f_name, getattr(output, f_name))

    for sub_name in output.__subsystems__:
        print('  Testing ', sub_name)
        sub = getattr(output, sub_name)
        for f_name in sub.__feats__:
            print('      ', f_name, getattr(sub, f_name))

    # Test action reading basic status
    print('Output status', output.read_output_status())
    output.clear_output_status()
    print('Voltage status', output.read_voltage_status())
    print('Measured output voltage', output.measure('voltage'))

    # Test settings and general behavior
