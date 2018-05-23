# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2018 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""I3py standard for DC sources.

"""
from i3py.core import HasFeatures, SubSystem, channel
from i3py.core.unit import FLOAT_QUANTITY
from i3py.core.actions import Action
from i3py.core.features import Bool, Float, Str, constant


class DCPowerSource(HasFeatures):
    """Standard interface expected from all DC Power sources.

    """

    #: Outputs of the source. By default we declare a single output on index 0.
    outputs = channel((0,))

    with outputs as o:

        #: Is the output on or off.
        #: Care should be taken that this value may not be up to date if a
        #: failure occurred. To know the current status of the output use
        #: read_output_status, this feature only store the target setting.
        o.enabled = Bool(aliases={True: ['On', 'ON', 'on'],
                                  False: ['Off', 'OFF', 'off']})

        #: Target voltage for the output. If the source is a "current" source
        #: this will likely be a fixed value.
        o.voltage = Float(unit='V')

        #: Range in which the voltage can be set.
        o.voltage_range = Float(unit='V')

        #: How does the source behave if it cannot reach the target voltage
        #: because it reached the target current first.
        #: - regulate: we stop at the reached voltage when the target current
        #:             is reached.
        #: - trip: the output is disabled if the current reaches or gets
        #:         greater than the specified current.
        o.current_limit_behavior = Str(constant('regulate'),
                                       values=('regulate', 'trip'))

        #: Target voltage for the output. If the source is a "voltage" source
        #: this will likely be a fixed value.
        o.current = Float(unit='A')

        #: Range in which the current can be set.
        o.current_range = Float(unit='A')

        #: How does the source behave if it cannot reach the target voltage
        #: because it reached the target current first.
        #: - regulate: we stop at the reached voltage when the target current
        #:             is reached.
        #: - trip: the output is disabled if the voltage reaches or gets
        #:         greater than the specified voltage.
        o.voltage_limit_behavior = Str(constant('regulate'),
                                       values=('regulate', 'trip'))

        @o
        @Action()
        def read_output_status(self) -> str:
            """Determine the status of the output.

            The generic format of the status is status:reason, if the reason is
            not known used 'unknown'. The following values correspond to usual
            situations.

            Returns
            -------
            status : {'disabled',
                      'enabled:constant-voltage',
                      'enabled:constant-current',
                      'tripped:over-voltage',
                      'tripped:over-current',
                      'unregulated'}
                The possible values for the output status are the following.
                - 'disabled': the output is currently disabled
                - 'enabled:constant-voltage': the target voltage was reached
                  before the target current and voltage_limit_behavior is
                  'regulate'.
                - 'enabled:constant-current': the target current was reached
                   before the target voltage and current_limit_behavior is
                   'regulate'.
                - 'tripped:over-voltage': the output tripped after reaching the
                  voltage limit.
                - 'tripped:over-current': the output tripped after reaching the
                  current limit.
                - 'unregulated': The output of the instrument is not stable.

            """
            raise NotImplementedError()


class DCPowerSourceWithMeasure(DCPowerSource):
    """DC power source supporting to measure the output current/voltage.

    """
    #: Outputs of the source. By default we declare a single output on index 0.
    outputs = channel((0,))

    with outputs as o:

        @o
        @Action()
        def measure(self, quantity: str, **kwargs) -> FLOAT_QUANTITY:
            """Measure the output voltage/current.

            Parameters
            ----------
            quantity : str, {'voltage', 'current'}
                Quantity to measure.

            **kwargs :
                Optional kwargs to specify the conditions of the measure
                (integration time, averages, etc) if applicable.

            Returns
            -------
            value : float or pint.Quantity
                Measured value. If units are supported the value is a Quantity
                object.

            """
            raise NotImplementedError()


class DCSourceTriggerSubsystem(SubSystem):
    """Subsystem handing the usual triggering mechanism of DC sources.

    It should be added to a DCPowerSource subclass under the name trigger.

    """
    #: Working mode for the trigger. This usually defines how the instrument
    #: will answer to a trigger event.
    mode = Str(values=('disabled',))

    #: Possible origin for trigger events.
    source = Str(values=('immediate', 'software'))  # Will extend later

    #: Delay between the trigger and the time at which the instrument start to
    #: modify its output.
    delay = Float(unit='s')

    @Action()
    def arm(self):
        """Make the system ready to receive a trigger event.

        """
        pass


class DCSourceProtectionSubsystem(SubSystem):
    """Interface for DC source protection.

    """
    #: Is the protection enabled.
    enabled = Bool(aliases={True: ['On', 'ON', 'On'],
                            False: ['Off', 'OFF', 'off']})

    #: How the output behaves when the low/limit is reached.
    behavior = Str(constant('trip'))

    #: Lower limit below which the setting is not allowed to go.
    low_level = Float()

    #: Higher limit above which the setting is not allowed to go.
    high_level = Float()

    @Action()
    def read_status(self) -> str:
        """Read the current status of the protection.

        Returns
        -------
        status : {'working', 'tripped'}

        """
        pass

    @Action()
    def reset(self) -> None:
        """Reset the protection after an issue.

        """
        pass
