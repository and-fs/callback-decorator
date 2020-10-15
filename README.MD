# Callback decorator package

This package contains a decorator for ensuring the call of a specific callback
argument - even when this callback is passed to other (decorated) functions.

## For what is it for?

If you ever had to deal with an asynchronous path which has to call a specific callback
as soon as the path has been left or the work had been finished, you know how hard
it can be to ensure to call such callback.

Instead of writing constructs like:

```python
def function_a(cb):
    """Senseless example"""
    try:
        if a == b:
            function_b(cb)
        else:
            print("what?")
    except Exception:
        cb()
        raise

def function_b(callback):
    try:
        call_something_else()
    finally:
        callback()
```

with this decorator you can write it like:

```python
@ensure_callback("cb")
def function_a(cb):
    if a == b:
        function_b(cb)
    else:
        print("what?")

@ensure_callback("callback")
def function_b(callback):
    call_something_else()
```

## How it works

The decorator extracts the callback argument and wraps it for detecting if the call has been made
or the argument has been passed to another decorated function.
If the decorated function, generator or coroutine is finished and the callback wasn't called,
it will be done by the decorator.

## Usage

The decorator `ensure_callback` needs at least the name of the callback argument as argument to itself:

`ensure_callback(callback_name:str, *args, **kwargs)`

``callback_name`` is the name of the argument (as string) which contains the callback in the decorated function:

```python
@ensure_callback("callme")
def my_function(a, b, callme):
    pass
```

All other arguments given to the decorator will be passed through to the callback when it is called by the decorator.

```python
def my_callback(name):
    print(f"callback from {name}")

@ensure_callback("cb", "decorator")
def my_function(b, cb):
    if b:
        cb("function")

my_function(True, my_callback)
# Output: "callback from function"

my_function(False, my_callback)
# Output: "callback from decorator"
```

Passing a name which is not an argument will raise a `ValueError`.

## Special cases

### Prevent the decorator callback

Sometimes it is not possible to build this chain (to decorate every function handling your callback).
For this case or to permit the decorator to call the callback, you can easily release it:

```python
def my_callback(name):
    print(f"callback from {name}")

def not_decorated(callme):
    callme("not_decorated")

@ensure_callback("callback", "decorated")
def decorated(callback):
    return

@ensure_callback("cb", "my_function")
def my_function(a, cb):
    if a:
        # release it from the decorator with `release_callback`
        not_decorated(release_callback(cb))
    else:
        decorated(cb)

my_function(True, my_callback)
# Output: callback from not_decorated

my_function(False, my_callback)
# Output: callback from decorated
```

### Use it in a generator

Of course this decorator can be used for generators, too:

```python
def my_callback(name):
    print(f"callback from {name}")

@ensure_callback("cb", "decorator")
def countdown(cb, start, stop = 0, step = 1):
    while (start := start - step) >= stop:
        yield start
    if stop > 0)
        cb("generator")

# countdown doesn't call `my_callback` because stop isn't greater than zero
for x in countdown(my_callback, 4):
    print(x)
# Output:
# 3
# 2
# 1
# callback from decorator

# countdown calls `my_callback`
for x in countdown(my_callback, 5, stop = 1):
    print(x)

# Output:
# 4
# 3
# 2
# callback from generator
```

### What about coroutines

You can use the decorator for coroutines, too.
Like for "normal" callables or generators the callback is called as soon as the coroutine or coroutine generator has finished it`s work without calling
the callback or passing it to another decorated callable.