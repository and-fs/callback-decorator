# -*- coding: utf8 -*-
"""
Tests for callback_decorator package.

:author: André Fritzsche-Schwalbe (andre.fritzsche@web.de)

:url: https://github.com/and-fs/callback-decorator

:license: MIT
"""
# ----------------------------------------------------------------------------------------------------------------------
import unittest
import callback_decorator
from typing import Tuple, Dict, Any, List, Callable
# ----------------------------------------------------------------------------------------------------------------------
NO_ARGS:Tuple[Tuple[Any,...], Dict[Any, Any]] = (tuple(), dict())
# ----------------------------------------------------------------------------------------------------------------------
class TestSimpleEnsureCallback(unittest.TestCase):
    """
    Tests für :mod:`callback_decorator` mit Stacktiefe 1.
    """

    def setUp(self):
        self.called = None

    def tearDown(self):
        self.called = None

    def callback_method(self, *args, **kwargs):
        self.called = (args, kwargs)

    def expect_callback(self, fu, *args, callback_args = NO_ARGS, **kwargs)->Any:
        self.called = None
        result:Any = fu(*args, **kwargs)
        self.assertEqual(self.called, callback_args)
        self.called = None
        return result

    def test_WrongArgRaisesValueError(self):
        """
        Dekorator mit falschem Argument-Namen.
        """
        with self.assertRaises(ValueError):
            @callback_decorator.ensure_callback("n/a")
            def mymethod(callback): # pylint: disable=unused-variable
                pass

    def test_CalledWhenException(self):
        """
        Callback muss gerufen werden, wenn die dekorierte Funktion mit Exception verlassen wurde.
        """
        @callback_decorator.ensure_callback("callback")
        def myfu(callback):
            raise RuntimeError("test")
        with self.assertRaises(RuntimeError):
            self.expect_callback(myfu, self.callback_method)

    def test_CalledWhenLeaving(self):
        """
        Callback muss gerufen werden, wenn die dekorierte Funktion ohne Aufruf verlassen wurde.
        """
        @callback_decorator.ensure_callback("callback")
        def myfu(callback):
            return 5
        result = self.expect_callback(myfu, self.callback_method)
        self.assertEqual(result, 5)

    def test_NotCalledWhenLeaving(self):
        """
        Callback darf nicht vom Dekorator gerufen werden, wenn der Aufruf in der dekorierten Funktion erfolgte.
        """
        @callback_decorator.ensure_callback("callback")
        def myfu(callback):
            callback(1)
            return "string_res"
        result = self.expect_callback(myfu, self.callback_method, callback_args = ((1,), {}))
        self.assertEqual(result, "string_res")

    def test_NotCalledWhenReleased(self):
        """
        Callback darf nicht vom Dekorator gerufen werden, wenn der Callback freigegeben wurde.
        """
        @callback_decorator.ensure_callback("callback")
        def myfu(callback):
            callback_decorator.release_callback(callback)
        result = myfu(self.callback_method)
        self.assertIsNone(self.called)
        self.assertIsNone(result)

    def test_NotCalledWhenReleasedWithException(self):
        """
        Callback darf nicht vom Dekorator gerufen werden, wenn der Callback freigegeben wurde.
        """
        @callback_decorator.ensure_callback("callback")
        def myfu(callback):
            callback_decorator.release_callback(callback)
            raise RuntimeError("test")
        with self.assertRaises(RuntimeError):
            myfu(self.callback_method)
        self.assertIsNone(self.called)
# ----------------------------------------------------------------------------------------------------------------------
class TestStackedEnsureCallback(unittest.TestCase):
    """
    Tests für :mod:`asyncprocesses.callback_decorator` mit Stacktiefe > 1.
    """

    def setUp(self):
        self.called = None
        self.calldepth = 0

    def tearDown(self):
        self.called = None
        self.calldepth = 0

    def callback_method(self, *args, **kwargs):
        self.called = (args, kwargs)

    def expect_callback(self, fu, *args, **kwargs):
        self.called = None
        fu(*args, **kwargs)
        self.assertEqual(self.called, kwargs.get('callback_args', NO_ARGS))
        self.called = None

    @callback_decorator.ensure_callback("callme")
    def DecoratedMethod(self, callchain:List[Callable], callme, *args, callit=True, callback_args=NO_ARGS, **kwargs):
        """
        :param callchain: Liste der zu rufenden Methoden. Bei jedem Ruf wird das jeweils erste Element entfernt und
            gerufen. Sobald die List dann leer ist, handelt es sich um den Endpunkt
            und der Rückruf erfolgt in Abhängigkeit zu ``callit``.

        :param callme: Das zu rufende Callback-Objekt (am Ende der Kette und nur dann, wenn ``callit`` mit ``True``
            evaluiert)

        :param callit: Gibt an, ob der Callback ``callme`` am Ende der Kette gerufen werden soll.
            Kann eine Instanz einer Ableitung von BaseException sein, in diesem Fall wird der Aufruf nicht
            ausgeführt sondern eine Exception ausgelöst.

        :param callback_args:

        :author: af
        """
        self.calldepth += 1
        if not callchain:
            if callit is not None:
                if isinstance(callit, BaseException):
                    raise callit
                if callit == 'Release':
                    callback_decorator.release_callback(callme)
                else:
                    callme(*callback_args[0], **callback_args[1])
        else:
            next_in_chain = callchain.pop(0)
            next_in_chain(callchain, callme, callit = callit, callback_args = callback_args, *args, **kwargs)

    def test_CalledWhenException(self):
        """
        Callback muss gerufen werden, wenn die dekorierte Funktion mit Exception verlassen wurde.
        """
        with self.assertRaises(RuntimeError):
            self.DecoratedMethod([self.DecoratedMethod,], self.callback_method, callit = RuntimeError("test"))
        self.assertEqual(self.calldepth, 2)

    def test_CalledWhenLeaving(self):
        """
        Callback muss gerufen werden, wenn die dekorierte Funktion mit Exception verlassen wurde.
        """
        self.expect_callback(self.DecoratedMethod, [self.DecoratedMethod,], self.callback_method, callit = None)
        self.assertEqual(self.calldepth, 2)

    def test_NotCalledWhenLeaving(self):
        """
        Callback darf nicht vom Dekorator gerufen werden, wenn der Aufruf in der dekorierten Funktion erfolgte.
        """
        self.expect_callback(
            self.DecoratedMethod, [self.DecoratedMethod, self.DecoratedMethod],
            self.callback_method, callit = True, callback_args = ((1,), {})
        )
        self.assertEqual(self.calldepth, 3)

    def test_NotCalledWhenReleased(self):
        """
        Callback darf nicht vom Dekorator gerufen werden, wenn der Callback freigegeben wurde.
        """
        self.expect_callback(
            self.DecoratedMethod, [self.DecoratedMethod, self.DecoratedMethod],
            self.callback_method, callit='Release', callback_args=None
        )
        self.assertEqual(self.calldepth, 3)
# ----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
