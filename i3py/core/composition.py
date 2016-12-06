# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright 2016 by I3py Authors, see AUTHORS for more details.
#
# Distributed under the terms of the BSD license.
#
# The full license is in the file LICENCE, distributed with this software.
# -----------------------------------------------------------------------------
"""Tools for customization of method using declarative syntax.

"""
from __future__ import (division, unicode_literals, print_function,
                        absolute_import)

from abc import abstractmethod, abstractproperty
from types import MethodType
from collections import OrderedDict, Mapping

from funcsigs import signature
from future.utils import with_metaclass, exec_

from .abstracts import (AbstractMethodCustomizer,
                        AbstractSupportMethodCustomization)


def normalize_signature(sig, alias=None):
    """Normalize a function signature for quick matching.

    Parameters
    ----------
    sig : Signature
        Function signature

    alias: unicode, optional
        Alias for self to use in signature.

    Returns
    -------
    normalized : tuple
        Tuple of strings matching the functions arguments, *args and **kwargs
        will have their * preceding.

    """
    def norm_arg(arg, alias):
        if alias and arg.name == 'self':
            return alias
        elif arg.kind == arg.VAR_POSITIONAL:
            return '*' + arg.name
        elif arg.kind == arg.VAR_KEYWORD:
            return '**' + arg.name
        else:
            return arg.name

    return tuple(norm_arg(p, alias) for p in sig.parameters.values())


class MetaMethodComposer(type):
    """Metaclass for method composer object offering custom instantiation.

    """
    sigs = {}

    def __call__(cls, obj, func, alias, chain_on=None, func_id='old',
                 signatures=None):
        """Create a custom subclass for each signature function.

        Parameters
        ----------
        obj : SupportMethodCustomization
            Object whose method is customized through the use of a
            MethodComposer.

        func : callable
            Original function this composer is replacing. This should be a
            function and not a bound method.

        alias : unicode
            Name to use to replace 'self' in method signature.

        chain_on : unicode
            Comma separated list of functions arguments that are also values
            returned by the function.

        func_id : unicode, optional
            Id of the original function to use in the composer.

        signatures : list, optional
            List of signatures to accept. If specified the signature of the
            passed function is ignored and the __call__ method will have the
            signature of the first specified signature.

        """
        if not signatures:
            sigs = [normalize_signature(signature(func), alias)]
        else:
            sigs = signatures

        id_ = (tuple(sigs), chain_on)
        if id_ not in MetaMethodComposer.sigs:
            subclass = cls.create_composer(func.__name__, sigs, chain_on)
            MetaMethodComposer.sigs[id_] = subclass

        custom_type = MetaMethodComposer.sigs[id_]
        return super(MetaMethodComposer, custom_type).__call__(obj, func,
                                                               alias, chain_on,
                                                               func_id,
                                                               sigs)

    def create_composer(cls, name, sigs, chain_on):
        """Dynamically create a subclass of base composer for a signature.

        """
        chain = chain_on or ''
        name = '{}Composer'.format(name)
        sig = sigs[0][1:]
        # Should store sig on class attribute
        decl = ('class {name}(cls):\n'
                '    __slots__ = ("sigs",)\n'
                '    def __call__(self{args}):\n'
                '         for m in self._methods:\n'
                '            {ret}m(self.__self__{args})\n'
                '         return {chain}'
                ).format(name=name, args=', ' + ', '.join(sig) if sig else '',
                         chain=chain, ret=chain + ' = ' if chain else '')
        glob = dict(cls=cls)
        exec_(decl, glob)
        return glob[name]


class MethodComposer(with_metaclass(MetaMethodComposer, object)):
    """Function like object used to compose feature methods calls.

    All methods to call are kept in an ordered fshion ensuring that they will
    be called in the right order while allowing fancy insertion based on method
    id.

    Parameters
    ----------
    obj : SupportMethodCustomization
        Object whose method is customized through the use of a MethodComposer.

    func : callable
        Original function this composer is replacing. This should be a function
        and not a bound method.

    alias : unicode
        Name to use to replace 'self' in method signature.

    chain_on : unicode
        Comma separated list of functions arguments that are also values
        returned by the function.

    func_id : unicode, optional
        Id of the original function to use in the composer.

    Notes
    -----
    Method ids must be unique and duplicate names are removed without warning.

    """
    __slots__ = ('__self__', '__name__', '_alias', '_chain_on', '_names',
                 '_methods', '_signatures')

    def __init__(self, obj, func, alias, chain_on, func_id='old',
                 signatures=None):
        self.__self__ = obj
        self.__name__ = func.__name__
        self._alias = alias
        self._chain_on = chain_on
        self._methods = [func]
        self._names = [func_id]
        self._signatures = signatures

    def clone(self, new_obj=None):
        """Create a full copy of the composer.

        """
        new = type(self)(new_obj or self.__self__, self, self._alias,
                         self._chain_on, '', self._signatures)
        new._names = self._names[:]
        new._methods = self._methods[:]
        return new

    def prepend(self, name, method):
        """Prepend a method to existing ones.

        Parameters
        ----------
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._check_duplicates(name)
        self._names.insert(0, name)
        self._methods.insert(0, method)

    def append(self, name, method):
        """Append a method to existing ones.

        Parameters
        ----------
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._check_duplicates(name)
        self._names.append(name)
        self._methods.append(method)

    def add_after(self, anchor, name, method):
        """Add the given method after a given one.

        Parameters
        ----------
        anchor : unicode
            Id of the method after which to insert the given one.
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._check_duplicates(name)
        i = self._names.index(anchor)
        self._names.insert(i+1, name)
        self._methods.insert(i+1, method)

    def add_before(self, anchor, name, method):
        """Add the given method before the specified one.

        Parameters
        ----------
        anchor : unicode
            Id of the method before which to insert the given one.
        name : unicode
            Id of the method. Used to find it when performing more complex
            operations on the list of methods.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        self._check_duplicates(name)
        i = self._names.index(anchor)
        self._names.insert(i, name)
        self._methods.insert(i, method)

    def replace(self, name, method):
        """Replace an existing method by a new one.

        Only custom methods can be replaced. Methods whose presence is
        linked to the feature kwargs cannot be replaced.

        Parameters
        ----------
        name : unicode
            Id of the method of the method to replace.
        method : MethodType
            Method bound to a feature which will be called when this object
            will be called.

        """
        i = self._names.index(name)
        self._methods[i] = method

    def remove(self, name):
        """Remove a method.

        Parameters
        ----------
        name : unicode
            Id of the method to remove.

        """
        i = self._names.index(name)
        del self._names[i]
        del self._methods[i]

    def reset(self):
        """Empty the composer.

        """
        self._names = []
        self._methods = []

    def __getitem__(self, key):
        return self._methods[self._names.index(key)]

    def __contains__(self, item):
        return item in self._names

    @property
    def __func__(self):
        return self

    def _check_duplicates(self, name):
        """Remove the name from the list to avoid having duplicate ids.

        """
        if name in self._names:
            msg = ('Cannot have duplicate ids in MethodComposer. (provided={},'
                   ' existing={})')
            raise ValueError(msg.format(name, self._names))


class customize(AbstractMethodCustomizer):
    """Marks a method to be used for customization of a descriptor method.

    Parameters
    ----------
    desc_name : unicode
        Name of the descriptor to customize.

    meth_name : unicode
        Name of the method of the descriptor to customize.

    specifiers : tuple, optional
        Tuple describing the modification. If ommitted the function will simply
        replace the existing behavior otherwise it will be used to update the
        MethodComposer in the adequate fashion.
        The tuple content should be :
        - kind of modification : 'prepend', 'add_before', 'add_after',
          'append', replace', 'remove'
        - argument to the modifier, not necessary for prepend and append.
          It should refer to the id of a previous modification.
        ex : ('add_after', 'old')

    modif_id : unicode, optional
        Id of the modification used to identify it.

    """
    __slots__ = ('desc_name', 'meth_name', 'specifiers', 'modif_id', 'func',
                 '__name__')

    def __init__(self, desc_name, meth_name, specifiers=(), modif_id='custom'):
        self.desc_name = desc_name
        self.meth_name = meth_name
        self.specifiers = specifiers
        self.modif_id = modif_id
        self.func = None

    def __call__(self, func):
        self.func = func
        self.__name__ = func.__name__
        return self

    def customize(self, owner, decorated_name):
        """Customize the object owned by owner.

        Parameters
        ----------
        owner : SupportMethodCustomization
            Class owning the descriptor to customize.

        decorate_name : unicode
            Name uder which the customization function appear in the class
            declaration.

        """
        spec = self.specifiers
        if not self.func and (not spec or spec[0] == 'remove'):
            raise RuntimeError('Need to decorate a function before calling '
                               'customize.')
        desc = getattr(owner, self.desc_name)
        assert isinstance(desc, AbstractSupportMethodCustomization),\
            ('Can only customize subclass of '
             'AbstractSupportMethodCustomization.')
        desc.modify_behavior(self.meth_name, self.func, self.specifiers,
                             self.modif_id)


class SupportMethodCustomization(AbstractSupportMethodCustomization):
    """Abstract class for objects supporting to have their method customized.

    Attributes
    ----------
    name : unicode
        Name of the object. Used in error reporting.

    """
    def __init__(self, *args, **kwargs):
        super(SupportMethodCustomization, self).__init__(*args, **kwargs)
        self.name = ''
        self._customs = OrderedDict()
        # Ids to use to refer to the old method when replacing it with a
        # composer.
        self._old_ids = {}

    @abstractmethod
    def analyse_function(self, meth_name, func, specifiers):
        """Analyse the possibility to use a function for a method.

        Parameters
        ----------
        meth_name : unicode
            Name of the method that should be customized using the provided
            function.

        func : callable
            Function to use to customize the method.

        specifiers : tuple
            Tuple describing the attempted modification.

        Returns
        -------
        specifiers : tuple
            Tuple describing the attempted modification. It is returned to
            allow altering it. The main use case is turning a complex operation
            in a replace because the base function is a no-op.

        signatures : list
            List of signatures that should be supported by a composer.

        chain_on : unicode
            Comma separated list of functions arguments that are also values
            returned by the function.

        Raises
        ------
        ValueError :
            Raised if the signature of the provided function does not match the
            one of the customized method.

        """
        pass

    @abstractproperty
    def self_alias(self):
        """Name used instead of self in function signature.

        """
        pass

    def modify_behavior(self, method_name, func, specifiers=(),
                        modif_id='custom', internal=False):
        """Alter the behavior of the Feature using the provided method.

        Those operations are logged into the _customs dictionary in OrderedDict
        for each method so that they can be duplicated by copy_custom_behaviors
        The storing format is as follow : method, name of the operation, args
        of the operation.

        Parameters
        ----------
        method_name : unicode
            Name of the method which should be modified.

        func : callable|None
            Function to use when customizing the feature behavior, or None when
            removing a customization.

        specifiers : tuple, optional
            Tuple used to determine how the function should be used. If
            ommitted the function will simply replace the existing behavior
            otherwise it will be used to update the MethodComposer in the
            adequate fashion.
            The tuple content should be :
            - kind of modification : 'prepend', 'add_before', 'add_after',
              'append', replace', 'remove'
            - argument to the modifier, not necessary for prepend and append.
              It should refer to the id of a previous modification.
            ex : ('add_after', 'old')

        modif_id : unicode, optional
            Id of the modification, used to refer to it in later modification.
            It is this id that can be specified as target for 'add_before',
            'add_after', 'replace', remove'.

        internal : bool, optional
            Private flag used to indicate that this method is used for internal
            purposes and that the modification makes no sense to remember as
            this won't have to be copied by copy_custom_behaviors.

        """
        # Intented full replacement should not have the id custom but 'old' to
        # match a previously present method.
        modif_id = modif_id if specifiers else 'old'

        # In case of non internal modifications (ie unrelated to object
        # initialisation) we keep a description of what has been done to be
        # able to copy those behaviors.
        # This is done before analysing the function to preserve the real
        # intented modification even if the analysis simplify it.
        if not internal:
            if not specifiers:
                self._customs[method_name] = func
            elif method_name not in self._customs:
                self._customs[method_name] = OrderedDict()
            elif not isinstance(self._customs[method_name], OrderedDict):
                old = self._customs[method_name]
                self._customs[method_name] = OrderedDict(old=(old,
                                                              ('prepend',)))

        # Check the function signature match the targeted method and return
        # the comma separated list of arguments on which the composed called
        # should be chained. Also attempt to simplify the modification if the
        # current function is known to be a no-op.
        if not specifiers or specifiers[0] != 'remove':
            specifiers, sigs, chain_on = self.analyse_function(method_name,
                                                               func,
                                                               specifiers)
        else:
            sigs, chain_on = None, None

        # In the absence of specifiers or for get and set we simply replace the
        # method.
        if not specifiers:
            # Preserve the id in case of future mofication
            self._old_ids[method_name] = modif_id
            setattr(self, method_name, MethodType(func, self))
            return

        # Otherwise we make sure we have a MethodsComposer.
        composer = getattr(self, method_name)
        if not isinstance(composer, MethodComposer):
            # Try to get a smart id from the object in case it was set by a
            # a previous modification.
            composer = MethodComposer(self, composer.__func__, self.self_alias,
                                      chain_on,
                                      self._old_ids.get(method_name, 'old'),
                                      signatures=sigs)

        # We now update the composer.
        composer_method_name = specifiers[0]
        composer_method = getattr(composer, composer_method_name)
        if composer_method_name in ('add_before', 'add_after'):
            composer_method(specifiers[1], modif_id, func)
        elif composer_method_name == 'replace':
            composer_method(specifiers[1], func)
        elif composer_method_name == 'remove':
            composer_method(specifiers[1])
        else:
            composer_method(modif_id, func)

        # Finally we update the _customs dict and reassign the composer.
        setattr(self, method_name, composer)
        if not internal:
            customs = self._customs[method_name]
            if composer_method_name == 'remove':
                del customs[modif_id]
            elif composer_method_name == 'replace':
                replaced = specifiers[1]
                if replaced in customs:
                    old = list(customs[replaced])
                    old[0] = func
                    customs[replaced] = tuple(old)
                else:
                    ind = composer._names.index(replaced)
                    if ind == 0:
                        customs[replaced] = (func, ('prepend',))
                    else:
                        n = composer._names[ind-1]
                        customs[replaced] = (func, ('add_after', n))
            else:
                op = (func, specifiers)
                customs[modif_id] = op

    def copy_custom_behaviors(self, obj):
        """Copy the custom behaviors existing on a feature to this one.

        This is used by set_feat to preserve the custom behaviors after
        recreating the feature with different kwargs. If an add_before or
        add_after clause cannot be satisfied because the anchor disappeared
        this method tries to insert the custom method in the most likely
        position.

        CAUTION : This method strives to build something that makes sense but
        it will most likely fail in some weird corner cases so avoid as mush as
        possible to use set_feat on feature modified using specially named
        method on the driver.

        """
        # Loop on methods which are affected by mofifiers.
        for meth_name, modifiers in obj._customs.items():
            if not isinstance(modifiers, Mapping):
                self.modify_behavior(meth_name, modifiers)
                continue

            # Loop through all the modifications.
            for custom, modifier in modifiers.items():

                func, specifiers = modifier
                method = getattr(self, meth_name)
                # In the absence of anchor we simply attempt the operation.
                if specifiers[0] not in ('add_after', 'add_before'):
                    self.modify_behavior(meth_name, func, specifiers, custom)

                # If the method is not a method composer there is no point in
                # attempting an operation involving an anchor.
                elif not isinstance(method, MethodComposer):
                    aux = {'add_after': ('append',),
                           'add_before': ('prepend',)}
                    self.modify_behavior(meth_name, func, aux[specifiers[0]],
                                         custom)

                # Otherwise we check whether or not the anchor exists and if
                # not try to find the most meaningfull one.
                else:
                    our_names = method._names
                    if specifiers[1] in our_names:
                        self.modify_behavior(meth_name, func, specifiers,
                                             custom)
                    else:
                        names = getattr(obj, meth_name)._names
                        # For add after we try to find an entry existing in
                        # both feature going backward (we will prepend at the
                        # worst), for add before we go forward (we will append
                        # in the absence of match).
                        shift = -1 if specifiers[0] == 'add_after' else -1
                        index = names.index(custom)
                        while index > 0 and index < len(names)-1:
                            index += shift
                            name = names[index]
                            if name in our_names:
                                self.modify_behavior(meth_name, func,
                                                     (specifiers[0], name),
                                                     custom)
                                shift = 0
                                break

                        if shift != 0:
                            op = ('prepend' if shift == -1 else 'append',)
                            self.modify_behavior(meth_name, func, op, custom)
