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

