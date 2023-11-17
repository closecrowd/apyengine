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

