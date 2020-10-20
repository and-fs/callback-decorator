# -*- coding: utf8 -*-
"""
Implementation of wrapper class and decorator for ensuring the single call of a function (callback)
passed through as an argument.

Example 1 (direct callback):
----------------------------

Callback is called by function (b) and not called by any decorator.

..code-block: python
    >>> def callback_function(description):
    ...    print (f"callback called from {description}")

    >>> @ensure_callback("cb", "decorator b")
    ... def function_b(cb):
    ...     cb("function_b")

    >>> @ensure_callback("callme", "decorator a")
    ... def function_a(callme):
    ...     function_b(callme)

    >>> function_a(callback_function)
    callback called from function_b

Example 2 (call by decorator):
------------------------------

Callback ist called by decorator (b) and not called by any decorator.

..code-block: python
    >>> def callback_function(description):
    ...    print (f"callback called from {description}")

    >>> @ensure_callback("cb", "decorator b")
    ... def function_b(cb):
    ...     return

    >>> @ensure_callback("callme", "decorator a")
    ... def function_a(callme):
    ...     function_b(callme)
    
    >>> function_a(callback_function)
    callback called from decorator b

Example 3 (release of callback):
--------------------------------

Callback is released by inner function (b) and due to this not called.

..code-block: python
    >>> def callback_function(description):
    ...    print (f"callback called from {description}")
    
    >>> @ensure_callback("cb", "decorator b")
    ... def function_b(cb):
    ...     release_callback(cb)
    
    >>> @ensure_callback("callme", "decorator a")
    ... def function_a(callme):
    ...     function_b(callme)

    >>> function_a(callback_function)

Example 4 (generator):
--------------------------------

Callback is released by inner function (b) and due to this not called.

..code-block: python
    >>> def callback_function(description):
    ...    print (f"callback called from {description}")
    
    >>> @ensure_callback("cb", "generator b")
    ... def generator_b(cb):
    ...     yield 1
    ...     yield 2

    >>> @ensure_callback("callme", "decorator a")
    ... def function_a(callme):
    ...     for x in generator_b(callme):
    ...         print (x)
    
    >>> function_a(callback_function)
    1
    2
    callback called from generator b

Of course you can use this patterns with coroutines and coroutine generators, too.

:author: André Fritzsche-Schwalbe (andre.fritzsche@web.de)

:url: https://github.com/and-fs/callback-decorator

:license: MIT
"""
# ----------------------------------------------------------------------------------------------------------------------
import asyncio
import inspect
from functools import wraps
from typing import Any, Callable, Union, Tuple, Generator
# ----------------------------------------------------------------------------------------------------------------------
class CallbackWrapper:
    """
    Wrapper for tracking a call to a callback object within the decorator :func:`ensure_callback`.
    """

    _callobj:Union[Callable, None]
    """
    Encapsulated callback object.
    ``None`` if the responsibility to it has been :meth:`release` d.
    """

    def __init__(self, callobj:Union["CallbackWrapper", Callable]):
        """
        :param callobj: The callback object to wrap.
            Can be either an instance of this class (in this case this instance takes the responsibility)
            or a callable to encapsulate here.
        """
        self._callobj = release_callback(callobj)

    def __call__(self, *args, **kwargs)->Any:
        """
        If this instance owns the call, it calls the encapsulated ``callobj`` with the given arguments,
        looses the responsibility and returns the result of the call.
        Otherwise nothing is done and ``None`` is returned.
        This means you can call it safely without caring about ownership (as long as you don`t need its result).
        """ 
        if self._callobj is not None:
            callobj:Callable = self._callobj
            self._callobj = None
            return callobj(*args, **kwargs)
        return None

    def release(self)->Callable:
        """
        Releases the encapsulated callback object and returns ist.

        :raises RuntimeError: If this instance didn`t have the responsibility of the callback object.
        """
        if self._callobj is None:
            raise RuntimeError("Cannot release a call object which is already released!")

        callobj:Callable = self._callobj
        self._callobj = None
        return callobj
# ----------------------------------------------------------------------------------------------------------------------
def release_callback(callobj:Union["CallbackWrapper", Callable])->Callable:
    """
    Releases an eventually wrapped callback ``callobj`` and returns the originally encapsulated callback object.
    Use this if you call a function which is not decorated with :func:`EnsureCallback`.

    :returns: The encapsulated callback object if ``callobj`` was wrapped by :class:`CallbackWrapper`,
        otherwise ``callobj`` as it is.

    :raise ValueError: If ``callobj`` was encapsulated but not owned by :class:`CallbackWrapper`.
        See :meth:`CallbackWrapper.Release` for details.
    """
    return callobj.release() if isinstance(callobj, CallbackWrapper) else callobj
# ----------------------------------------------------------------------------------------------------------------------
def _bindargs_and_get_callobj(
    signature:inspect.Signature,
    callback_name:str,
    *args, **kwargs)->Tuple[CallbackWrapper, inspect.BoundArguments]:
    """
    Binds arguments ``*args`` and ``**kwargs`` to the given ``signature`` and applies the defaults to it.
    Wraps the argument named ``calback_name`` by an instance of :class:`CallWrapper`.

    :returns: A tuple of the wrapped callback from argument ``callback_name`` and the bound arguments.
    """
    bound_arguments:inspect.BoundArguments = signature.bind(*args, **kwargs)
    bound_arguments.apply_defaults()

    callback_obj:CallbackWrapper = CallbackWrapper(bound_arguments.arguments[callback_name])
    bound_arguments.arguments[callback_name] = callback_obj
    return (callback_obj, bound_arguments)
# ----------------------------------------------------------------------------------------------------------------------
def ensure_callback(callback_name:str, *callback_args, **callback_kwargs):
    """
    Decorator to ensure calling of a callback argument.

    The callback will be called with the optional ``callback_args`` and ``callback_kwargs``, except if:
        - the callback has been passed to another callable decorated with this decorator
        - the callback has been called inside the decorated function
        - the callback has been released (see :func:`release_callback`)

    :param callback_name: name of the argument of the decorated function which contains the callback

    :raise ValueError: If the decorated function doesn`t have a parameter named ``callback_name``.
    """
    def decorator(funcobj:Callable)->Callable:
        sig:inspect.Signature = inspect.signature(funcobj)

        if callback_name not in sig.parameters:
            raise ValueError(f"Wrapped function '{funcobj.__name__}' has no parameter '{callback_name}'!")

        # async def ... (coroutine)
        if inspect.iscoroutinefunction(funcobj):
            @wraps(funcobj)
            async def wrapper(*args, **kwargs)->Callable:
                callback_obj, bound_arguments = _bindargs_and_get_callobj(sig, callback_name, *args, **kwargs)
                try:
                    return await funcobj(*bound_arguments.args, **bound_arguments.kwargs)
                finally:
                    callback_obj(*callback_args, **callback_kwargs)
        
        # async def ... with yield (coroutine generator)
        elif inspect.isasyncgenfunction(funcobj):
            @wraps(funcobj)
            async def wrapper(*args, **kwargs)->Callable:
                callback_obj, bound_arguments = _bindargs_and_get_callobj(sig, callback_name, *args, **kwargs)
                try:
                    async for x in funcobj(*bound_arguments.args, **bound_arguments.kwargs):
                        yield x
                finally:
                    callback_obj(*callback_args, **callback_kwargs)
        
        # def ... with yield (generator)
        elif inspect.isgeneratorfunction(funcobj):
            @wraps(funcobj)
            def wrapper(*args, **kwargs)->Generator:
                callback_obj, bound_arguments = _bindargs_and_get_callobj(sig, callback_name, *args, **kwargs)
                try:
                    yield from funcobj(*bound_arguments.args, **bound_arguments.kwargs)
                finally:
                    callback_obj(*callback_args, **callback_kwargs)

        # def ... (normal function / method)
        else:
            @wraps(funcobj)
            def wrapper(*args, **kwargs)->Any:
                callback_obj, bound_arguments = _bindargs_and_get_callobj(sig, callback_name, *args, **kwargs)
                try:
                    return funcobj(*bound_arguments.args, **bound_arguments.kwargs)
                finally:
                    callback_obj(*callback_args, **callback_kwargs)

        return wrapper

    return decorator
# ----------------------------------------------------------------------------------------------------------------------
