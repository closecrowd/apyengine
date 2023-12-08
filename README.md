# apyengine
	Version 1.0

ApyEngine is an interpreter for a Python-subset language, written in Python3.  It's easily embedded in a Python application, and provides a means to add safe scripting.  It great for education - teaching programming concepts in a secure environment.  Or giving the users of your application the ability to write their own scripts, without introducing security issues.

At it's heart is a fork and extension of [asteval](https://github.com/newville/asteval)  by Matt Newville, with many, many new features and abilities.  

For an example of fully utilizing the engine, see the companion project [apyshell](https://github.com/closecrowd/apyshell).
        
Some of the major features:

-  Familiar - Python syntax, easy to learn.
- Embeddable - It's easy to run scripts from your application, and interact  with the script's environment.
- Extensible - Add-on modules provide extra features as needed.  And it's easy to  create your own modules.
- Powerful - Most of the core Python 3 functionality, with easy multi-threading support.
- Secure - The host application determines which modules and extensions are available to the scripts.  Scripts can not break out and compromise the host system.
        
There are some major differences from standard Python.  Scripts can not import Python modules, and can not define classes (as of Version 1).  Any Python function that would allow a script to affect the host system is blocked or re-defined.

Python elements that are **not** allowed include:

**import, eval, exec, getattr, lambda, class, global, yield, Generators,  Decorators**

and a few others.
         
The documentation in the docs/ diectory has more details about the language and engine APIs.

It currently runs on Linux, and tested with Python 3.5 to 3.9.  Ports to Android, Windows, and MacOS are underway.


### History

The seeds of this project started a few years ago.  I had written an Android application for cellular engineers that performed a variety of network tests, and logged the results.  It worked well, but adding new test functionality meant re-releasing the app, which became tiresome.

I wanted to give the RF engineers the ability to add new tests, and maybe create their own.  That meant a scripting language, easy to code in, and with support for their specific needs.  And it had to be safe, so a rogue or defective script could not compromise the test devices.

I could have created a new scripting language, but I picked Python for it's flexibility and vast training resources.  The .apy language ***is*** Python, just restricted.

The original prototype of the new app was written in Python 2,7, using Kivy as it's UI on Android.  It worked, but was pretty primitive compared to the current version.

The project ran it's source, and the app was retired.  I took the basic concepts, rewrote the entire codebase from scratch in Python 3, and began using it my own networks.  The engine is embedded in my apyshell framework, and has been running system management and Home Automation tasks for a few years now.

### Installation

Grab the "[apyengine](https://github.com/closecrowd/apyengine/)" project from GitHub, and change to the top-level directory (where this README is located).  Then just:

```sudo pip install .```

and it will be installed in your global Python site library.  If you want to work with the sources while using it, you can also do:

```sudo pip install -e .```

for an in-place, editable install.

### Running

The simplest invocation of the engine would look something like this:

```python
import apyengine

# create the scripting engine
engine = apyengine.ApyEngine()

# load and run the primary script
engine.loadScript_("myscriptname")
```

This runs a script named "myscriptname.apy" in the current directory.    You can perform actions like setting variables before the script is run:

```python
# pass in the name of this machine
engine.setSysVar_('hostname',  platform.node())
```

You can also directly feed it Python expressions, and get the results:

```python
ret = engine.eval_("1 + 1")
print(ret)
```

See the documentation for the full list of API commands.

### Examples

Here's a very simple example of the core syntax.  This doesn't use any of the add-on extensions or features.  In fact, it'll execute under regular Python as well:

```python
def primes_sieve(limit):

    limitn = limit + 1
    primes = list(range(2, limitn))

    for i in primes:
        factors = list(range(i, limitn, i))

        for f in factors[1:]:
            if f in primes:
                primes.remove(f)

    return primes


p = primes_sieve(20000)
print(p)
```

Here's another one (included in this package as 'examples/apyexample1.py'):

```python
#!/usr/bin/env python3
"""apyexample1.py

A simple example showing how to create and use the apyengine interpreter
directly.

This is the most basic possible useage - running a single Python statement.
It shows how to instanciate the engine and call it to execute a statement.
If the statement returns a value (i.e. it would print on the console if
entered into Python directly), then it will return it to you.  This might
be useful in your application.

State is preserved across eval_() calls.

Credits:
    * version: 1.0
    * last update: 2023-Nov-17
    * License:  MIT
    * Author:  Mark Anacker <closecrowd@pm.me>
    * Copyright (c) 2023 by Mark Anacker

"""

import apyengine

# create the scripting engine
engine = apyengine.ApyEngine('.', False)

# use it to evaluate a statement
ret = engine.eval_("print('Hello, World!')")
# if there was a problem (a None return means no errors)
if ret:
    # print the returned error message
    print(ret)

# this one returns a value from the expression
ret = engine.eval_("1024 * 64")
print(ret,"should be enough for anyone...")


# we're done

```

And the last one, which is a simple REPL:

```python
#!/usr/bin/env python3
"""apyexample2.py

A simple example showing how to create and use the apyengine interpreter
directly.

This example show a simple REPL (Read-Execute-Print-Loop) executing
statements in the engine.

State is preserved across eval_() calls, so you can enter multiple lines,
like this:

> python3 apyexample2.py
a = 1
b = 2
print(a + b)
-->  3
^c

You can even use the installable modules (NOT extensions):

> python3 apyexample2.py
install_('time')
print('Right now, it is:', asctime_(localtime_()))
^c


Credits:
    * version: 1.0
    * last update: 2023-Nov-17
    * License:  MIT
    * Author:  Mark Anacker <closecrowd@pm.me>
    * Copyright (c) 2023 by Mark Anacker

"""

import sys
import apyengine

# create the scripting engine
engine = apyengine.ApyEngine('.', False)

# run until ^c
while True:
    # read a line from the console
    inl = sys.stdin.readline().rstrip('\n')
    if inl:
        # and execute it in the engine
        engine.eval_(inl)


# we're done

```
