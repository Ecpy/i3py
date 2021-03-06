# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016-2017 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Base class for instrument channels.

"""
from typing import (Any, Callable, ClassVar, Dict, Hashable, Iterable,
                    Optional, Tuple, Type, Union)

from .abstracts import (AbstractChannel, AbstractChannelContainer,
                        AbstractChannelDescriptor, AbstractFeature,
                        AbstractHasFeatures)
from .base_subsystem import SubSystem
from .utils import check_options


class ChannelContainer(object):
    """Default container storing references to the instrument channels.

    Note that is the responsibility of the user to check that a channel is
    available before querying it.

    Parameters
    ----------
    cls : class
        Class of the channel to instantiate when a channel is requested.

    parent : HasFeatures
        Reference to the parent object holding the channel.

    name : str
        Name of the channel subpart on the parent.

    list_available : callable
        Function to call to query the list of available channels.

    aliases : dict
        Dict mapping channel ids to aliases names.

    """

    def __init__(self, cls: Type[AbstractChannel], parent: AbstractHasFeatures,
                 name: str, list_available: Callable, aliases: dict) -> None:
        self._cls = cls
        self._channels: Dict[Hashable, AbstractChannel] = {}
        self._name = name
        self._parent = parent
        self._list = list_available
        self._aliases: Dict[Hashable, Any] = {}
        # So far aliases map ch_ids to possible aliases. To identify an alias
        # we need to invert this mapping.
        for k, v in aliases.items():
            if isinstance(v, (tuple, list)):
                for nk in v:
                    self._aliases[nk] = k
            else:
                self._aliases[v] = k

    @property
    def available(self) -> list:
        """List the available channels.

        """
        return self._list(self._parent)

    @property
    def aliases(self) -> dict:
        """List the aliases.

        """
        return self._aliases.copy()

    def __getitem__(self, ch_id: Any) -> AbstractChannel:
        if ch_id in self._aliases:
            ch_id = self._aliases[ch_id]

        if ch_id in self._channels:
            return self._channels[ch_id]

        chs = self.available
        if ch_id not in chs:
            msg = f'{ch_id} is not listed among the available channels: {chs}'
            raise KeyError(msg)

        parent = self._parent
        ch = self._cls(parent, ch_id,
                       caching_allowed=parent._use_cache
                       )
        self._channels[ch_id] = ch
        return ch

    def __iter__(self) -> Iterable[AbstractChannel]:
        for id in self.available:
            yield self[id]


AbstractChannelContainer.register(ChannelContainer)


class Channel(SubSystem):
    """Channels are used to represent instrument channels identified by a id
    (a number generally).

    They are similar to SubSystems in that they expose a part of the
    instrument capabilities but multiple instances of the same channel
    can exist at the same time under the condition that they have different
    ids.

    By default channels passes their id to their parent when they call
    default_*_feat as the kwarg 'ch_id' which can be used by the parent
    to direct the call to the right channel. The exact kwarg used can be
    overwritten using the CHANNEL_ID class attribute.

    Parameters
    ----------
    parent : HasFeat
        Parent object which can be the concrete driver or a subsystem or
        channel.
    id :
        Id of the channel used by the instrument to correctly route the calls.

    Attributes
    ----------
    id :
        Id of the channel used by the instrument to correctly route the calls.

    """
    #: Class variable used to control under what name the channel id is passed
    #: to the parent inside default_get_feature and default_set_feature.
    CHANNEL_ID: ClassVar[str] = 'ch_id'

    def __init__(self, parent: AbstractHasFeatures, id: Any, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.id = id

    def default_get_feature(self, feat: AbstractFeature, cmd: Any,
                            *args, **kwargs) -> Any:
        """Channels simply pipes the call to their parent.

        """
        kwargs[self.CHANNEL_ID] = self.id
        return self.parent.default_get_feature(feat, cmd, *args, **kwargs)

    def default_set_feature(self, feat: AbstractFeature, cmd: Any,
                            *args, **kwargs):
        """Channels simply pipes the call to their parent.

        """
        kwargs[self.CHANNEL_ID] = self.id
        return self.parent.default_set_feature(feat, cmd, *args, **kwargs)

    def default_check_operation(self,
                                feat: AbstractFeature,
                                value: Any,
                                i_value: Any,
                                response: Any=None) -> Tuple[bool, Any]:
        """Channels simply pipes the call to their parent.

        """
        return self.parent.default_check_operation(feat, value, i_value,
                                                   response)


AbstractChannel.register(Channel)


class ChannelDescriptor(object):
    """Descriptor giving access to a channel container.

    The channel container is returned only if the proper conditions are matched
    in terms of static options (as specified through the options of the
    channel declarator).

    """
    __slots__ = ('cls', 'name', 'options', 'container', 'list_available',
                 'aliases')

    def __init__(self, cls: Type[AbstractChannel], name: str, options: str,
                 container: Type[AbstractChannelContainer],
                 list_available: Callable,
                 aliases: dict) -> None:
        self.cls = cls
        self.name = name
        self.options = options
        self.container = container
        self.list_available = list_available
        self.aliases = aliases

    def __get__(self,
                instance: Optional[AbstractHasFeatures],
                cls: Optional[Type['ChannelDescriptor']]=None
                ) -> (Union[AbstractChannelContainer, Type[AbstractChannel]]):
        if instance is None:
            return self.cls
        else:
            if self.name not in instance._channel_container_instances:
                if self.options:
                    test, msg = check_options(instance, self.options)
                    if not test:
                        ex_msg = ('%s is not accessible with instrument '
                                  'options: %s')
                        raise AttributeError(ex_msg % (self.name, msg))

                cc = self.container(self.cls, instance, self.name,
                                    self.list_available, self.aliases)
                instance._channel_container_instances[self.name] = cc

            return instance._channel_container_instances[self.name]


AbstractChannelDescriptor.register(ChannelDescriptor)
