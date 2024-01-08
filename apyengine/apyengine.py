#!/usr/bin/env python3
"""apyengine - An environment for running Python-subset scripts.

This module implements an interpreter for a Python3 subset, along with support
functions.  It may be embedded in a Python3 host program to provide versatile
and extensible scripting.  The syntax is Python3, with some significant
limitations.  To wit - no classes, no importing of Python modules, and no
dangerous functions like 'exec()'.  This adds a great degree of security when
running arbitrary scripts.

Some pre-determined Python modules (such as numpy) may be installed into the
interpreter by scripts.  Additional optional functionality is provided by
extensions.  These are full Python scripts that may be loaded on-demand by
the user scripts.  There are many extensions provided in the distribution,
and it's easy to create new ones.

The companion project "apyshell" demonstrates how to fully use and control
this engine.
<https://github.com/closecrowd/apyshell>

Credits:
    * version: 1.0.0
    * last update: 2023-Nov-17
    * License:  MIT
    * Author:  Mark Anacker <closecrowd@pm.me>
    * Copyright (c) 2023 by Mark Anacker

Note:
    This package incorporates "asteval" from https://github.com/newville/asteval

"""

import sys
import os
import string
from types import *
from os.path import exists

import gc

from .asteval import Interpreter
from .astutils import valid_symbol_name

##############################################################################

#
# Globals
#

DEFAULT_EXT = '.apy'        # default extension for scripts

# chars we allow in file names (or other user-supplied names)
# a-zA-Z0-9_-
VALIDCHARS = string.ascii_letters+string.digits+'_-'

##############################################################################


# ----------------------------------------------------------------------------
#
# Engine class
#
# ----------------------------------------------------------------------------

class ApyEngine():
    """Create an instance of the ApyEngine script runner.

    This class contains the interpreter for the apy language, as well as full
    support structures for controlling it's operation.  It is intended for this
    class to be instanciated in a host application that will perform the support
    functions, and control this engine.

    """

    def __init__(self, basepath=None, builtins_readonly=True, global_funcs=False,
                    writer=None, err_writer=None):

        """Constructs an instance of the ApyEngine class.

        Main entry point for apyengine.  It also installs all of the script-
        callable utility functions.

            Args:

                basepath            : The top directory where script files will be found.
                                        (default=./)

                builtins_readonly   : If True, protect the built-in symbols from being
                                        overridden (default=True).

                global_funcs        : If True, all variables are global, even in
                                        def functions.
                                    : If False, vars created in a def func are local to
                                        that func (default=False).
                                        Can also be modified by setSysFlags_()

                writer              : The output stream for normal print() output.
                                        Defauls to stdout.

                err_writer          : The output stream for errors. Defaults to stderr.

            Returns:

                Nothing.

        """

        self.__writer = writer or sys.stdout
        self.__err_writer = err_writer or sys.stderr

        self.__usersyms = {}
        self.__persistprocs = []
        self.__systemVars = {}
        # list of installs
        self.__installs = []


        # load the interpreter
        self.__ast = Interpreter(writer=writer, err_writer=err_writer,
                            builtins_readonly=builtins_readonly, global_funcs=global_funcs,
                            raise_errors=False)

        # set a flag is we're on Windows
        if sys.platform.startswith('win'):
            self.__windows = True
        else:
            self.__windows = False

        # if no base path for the scripts was given, use the current directory
        if basepath is None or len(basepath) == 0:
            if self.__windows:
                self.__basepath = []
            else:
                self.__basepath = ['./']
        else:
            if type(basepath) is list:
                self.__basepath = basepath
            else:
                self.__basepath = basepath.split(',')

        self.__abort = False
        self.__lastScript = ''    # name of the most-recent script

        # register these methods as script-callable funcs
        self.regcmd("setSysFlags_", self.setSysFlags_)
        self.regcmd("getSysFlags_", self.getSysFlags_)

        self.regcmd("eval_", self.eval_)
        self.regcmd("check_", self.check_)
        self.regcmd("getSysVar_", self.getSysVar_)
        self.regcmd("install_", self.install_)
        self.regcmd("listModules_", self.list_Modules_)
        self.regcmd("loadScript_", self.loadScript_)
        self.regcmd("isDef_", self.isDef_)
        self.regcmd("listDefs_", self.listDefs_)
        self.regcmd("getvar_", self.getvar_)
        self.regcmd("setvar_", self.setvar_)

        self.regcmd("stop_", self.stop_)

        self.regcmd("exit_", self.exit_)

    # dump the symbol table
    def dumpst_(self, tag=None):
        dump(self.__ast.symtable, tag)

    # dump the user symbol table
    def dumpus_(self):
        dump(self.__usersyms)

    # return an error message
    def reporterr_(self, msg):
        """Print error messages on the console error writer.

        Prints an error message and returns it.

            Args:
                msg :   The message to output, and return

            Returns:

                The passed-in error message

        """

        if msg:
            print("!!! "+msg, file=self.__err_writer)
        return msg

#
# engine API
#

    # not currently implemented - for future use
    def setSysFlags_(self, flagname,  state):
        if not self.__ast:
            return False

        if state not in { True,  False }:
            return False

        return False

    # not currently implemented - for future use
    def getSysFlags_(self, flagname):
        if not self.__ast:
            return False

        if state not in { True,  False }:
            return False

        return False

    # set a value in the system dict
    def setSysVar_(self, name, val):
        """Sets the value of a system var.

        Sets a value in the engine-maintained table.  These values may
        be read by scripts using the "getSysVar_()" function.  A list of
        the var names is saved in a script-accessible names "_sysvars_".

        This method is NOT exposed to the scripts.

            Args:

                name    :   The name to store the value under.

                val     :   The value to store. If None, remove the name from
                the table.

            Returns:

                True if success, False if there was an error.

        """

        if not name:
            return False
        try:
            # don't allow replacing the keys list
            if name == '_sysvars_':
                return False

            # if val == None, delete the entry
            if val is None:
                # if it's in the table
                if name in self.__systemVars:
                    del self.__systemVars[name]
            else:
                # otherwise, store a new one
                self.__systemVars[name] = val
            # save a list of the symbols in a script-accessible variable
            self.__systemVars['_sysvars_'] = list(self.__systemVars.keys())
            return True
        except:
            return False

    # stop the script ASAP
    def abortrun(self):
        """Stop a script as soon as possible.

        This function sets a flag that the Interpreter check as often
        as possible.  If the flag is set, of the script is halted and
        control returns to the host program.

        """

        if self.__ast:
            self.__abort = True
            try:
                self.__ast.abortrun()
            except Exception as e:
                print("abort error:"+str(e))

    # add a new command
    def regcmd(self, name, func=None):
        """Register a new command for the scripts to use.

        This method adds a function name and a reference to it's
        implementation to the script's symbol table.  This is how
        Extensions add their functions when they are loaded (via
        the extensionapi).  It's also how THIS module makes the
        following methods available to the scripts (when applicable).

        It can be called on it's own to add a single function name,
        or by the addcmds() to add a bunch at once.  It can also be
        called directly by the host application to give scripts access
        to custom commands.

            Args:

                name    :   The function name to add

                func    :   A reference to it's implementation

            Returns:

                True if the command was added, False if not

        Note: see addcmds() below

        """

        if not name or len(name) < 1:
            return False

        # if it's a valid name
        if valid_symbol_name(name):
            # and has a function body
            if func is not None:
                # add or replace in the table
                self.__ast.addSymbol(name, func)
                # and add the name to the RO table if it isn't already
                if name not in self.__ast.readonly_symbols:
                    self.__ast.readonly_symbols.add(name)
                return True
        return False

    # remove a registered command
    def unregcmd(self, name):
        """Unregister a command.

        Removes a function name and reference from the symbol
        table, making it inaccessible to scripts.  This is used
        to UNload an extension.

            Args:

                name    :   The function name to remove

            Returns:

                True if the command was deleted, False if not

        Note: see delcmds() below

        """

        if not name or len(name) < 1:
            return False

        # if it's a valid name
        if asteval.valid_symbol_name(name):
            self.__ast.delSymbol(name)
            if name in self.__ast.readonly_symbols:   # set
                self.__ast.readonly_symbols.remove(name)
            return True
        return False

    # add new built-in commands after init
    def addcmds(self, cmddict):
        """Register a whole dict of new commands for the scripts to use.

        This method adds multiple name:definition pairs into the symbol
        table at once.  It's more convenient than calling regcmd() for
        each one.

        This method is called by the registerCmds() method in the
        ExtensionAPI class.  This is how Extensions add their functions
        when they load.

            Args:

                cmddict :   A dict with name:reference pairs

            Returns:

                True if the arguments were valid, False otherwise

        """

        if cmddict is not None:
            if type(cmddict) is dict:
                for k, v in cmddict.items():
                    self.regcmd(k, v)
                # note: we don't check the return of each item
                return True
        return False

    def delcmds(self, cmddict):
        """Unregister a whole dict of existing commands.

        This method deletes multiple name:definition pairs from the symbol
        table at once.  It's more convenient than calling unregcmd() for
        each one.

        This method is called by the unregisterCmds() method in the
        ExtensionAPI class.  This is how Extensions clean up when they
        are unloaded.

            Args:

                cmddict :   A dict with name:reference pairs

            Returns:

                True if the arguments were valid, False otherwise

        """

        if cmddict is not None:
            if type(cmddict) is dict:
                for k, v in cmddict.items():
                    # note: we don't check the return of each item
                    self.unregcmd(k)
                return True
        return False

#
# script proc persistence
# these methods are useful to host frameworks that want to
# manage script libraries.
#

    # add or remove a proc in the persist list
    def setProcPersist(self, pname, flag):
        """Add or remove the proc from the persist list.

        This list protects script-defined functions from the
        clearProcs() function.  This just modifies the persist list -
        it doesn't affect the presence of the proc in the engine itself.

            Args:

                pname   :   The name of the def func() to presist (or not)
                flag    :   if True, add it to the persist list. if False, remove it

            Returns:

                The return value. True for success, False otherwise.

        """

        # setting persist state
        if flag is True:
            # already in there?
            if pname in self.__persistprocs:
                return True
            else:
                self.__persistprocs.append(pname)
                return True
        # resetting the state
        else:
            # already in there?
            if pname in self.__persistprocs:
                # remove it
                try:
                    pindex = self.__persistprocs.index(pname)
                    del self.__persistprocs[pindex]
                except:
                    pass
                return True
        return False

    # remove a specified proc from the engine (and the persist list if needed)
    def delProc(self, pname):
        """Remove a specified proc from the engine (and the persist list if
        needed).

        This effectively over-rides the setProcPersist() setting.

            Args:

                pname   :   The name of the def func() to remove

            Returns:

                The return value. True for success, False otherwise.

        """

        if pname in self.__ast.symtable:
            if type(self.__ast.symtable[pname]) == asteval.asteval.Procedure:
                # and take it out of the symbol table
                self.__ast.delSymbol(pname)
                # is this a persistent one?
                if pname in self.__persistprocs:
                    try:
                        pindex = self.__persistprocs.index(pname)
                        del self.__persistprocs[pindex]
                    except:
                        pass
                    return True
        return False

    # remove all currently-defined def functions
    def clearProcs(self, exception_list=None):
        """Remove all currently-defined def functions *except* those on
        the persistence list *or* in the passed-in exception_list.

        Used to remove all "def funcs()" created by the script.  Most
        useful when you're loading a new script programmatically.

            Args:

                exception_list  :   A list[] of proc names to NOT remove.

            Returns:

                None

        """

        klist = []

        # make a list of all of the def func() created by the script
        for k in self.__ast.symtable:
            if type(self.__ast.symtable[k]) == asteval.asteval.Procedure:
                # skip the persistent ones
                if k not in self.__persistprocs:
                    klist.append(k)

        # did we find any?
        if len(klist) < 1:
            return

        # walk the list of procs
        for k in klist:
            # if we have an exception list
            if exception_list is not None:
                # and this proc is on it
                if k in exception_list:
                    # don't remove
                    continue
            # otherwise take it out of the symbol table
            # this de-references it
            self.__ast.delSymbol(k)
        # clean up the heap
        gc.collect()

#
# Script-callable functions
#

    # directly execute a script statement
    def eval_(self, cmd):
        """Directly execute a script statement in the engine.

        Executes a Python statement in the context of the current Interpreter -
        as if it was in a script.  This can set/print variables, run user
        def funcs(), and so forth.  It can be use to make a simple REPL
        program.

        This function can be called from within a script ("eval_()"), or from
        the host application.

            Args:

                cmd :   An expression to execute

            Returns:

                The results of the expression or None if there was an error

        """

        if not cmd:
            return None

        rv = None
        try:
            rv = self.__ast.eval(cmd)
        except Exception as e:
            print("eval error:"+str(e))
            # return the error message to the caller
            return self.reporterr_("ERR in command: "+str(e))
        return rv

    # syntax check an expression
    def check_(self, code):
        """Syntax check a Python expression.

        Given a string containing a Python expression, parse it and
        return OK if it's valid, or an error message if not.

        This function can be called from within a script ("check_()"), or from
        the host application.

            Args:

                code    :   An expression to check

            Returns:

                'OK' if the expression is valid
                'ERR' and a message if it isn't valid
                None if code is empty

        """

        if not code:
            return None
        try:
            self.__ast.parse(code)
            return 'OK'
        except Exception as e:
            return self.reporterr_("ERR in code: "+str(e))

    # install a pre-authorized Python module into the engine's symbol table
    def install_(self, modname):
        """Install a pre-authorized Python module into the engine's symbol table.

        This is callable from a script with the 'install_()' command.  Only modules
        in the MODULE_LIST list in astutils.py can be installed.  Once installed,
        they can not be uninstalled during this run of apyshell.

            Args:

                modname :   The module name to install

            Returns:

                The return value. True for success, False otherwise.

        """

        if not modname:
            return False

        # if we haven't installed it already
        if modname not in self.__installs:
            # if the module installed
            if self.__ast.install(modname):
                # add it to our local list
                self.__installs.append(modname)
                return True
        # something went wrong
        return False

    # return the list of installed modules
    def list_Modules_(self):
        """Returns a list[] of installed modules.

        Returns a list of the built-in modules installed with the
        "install_()" command.

            Args:

                None

            Returns:

                A list of installed modules (not Extensions).

        """
        return self.__installs

    # load and execute a script file
    def loadScript_(self, filename, persist=False):
        """Load and execute a script file.

        This method loads a script file (the .apy extension will be
        added if needed), then executes it.  This is called by the host
        application to run a script.  It can also be called within a
        script with the "loadScript_()" command to do things like loading
        library functions or variables.

        Files are loaded relative to the basepath passed to the engine at
        init time.

        The persist flag is used by frameworks that want to retain some script-
        defined funcs (such as libraries), while removing others.  See the
        clearProcs() method.

            Args:

                filename    :   The name of the script file (.apy)

                persist     :   If True, mark any functions defined as persistent.

            Returns:

                None if the script executed, an error message if not.

        """

        if not filename:
            return self.reporterr_("Error loading script - Missing filename")

        # clean up the submitted filename
        sfilename = sanitizePath(filename)

        # verify the file name
        # no quoting (*nix systems only)

        if not checkFileName(sfilename):
            return self.reporterr_("Error loading script '"+filename+"': Invalid filename")
        filename = sfilename

        # add the extension if needed
        if filename[-4:] != DEFAULT_EXT:
            filename += DEFAULT_EXT

        # find the file on the script path(s)
        fn = findFile(self.__basepath, filename)
        if not fn:
            return self.reporterr_("Error - unknown script '"+filename+'"')

        try:
            # add the extension if needed
            if fn[-4:] != DEFAULT_EXT:
                fn += DEFAULT_EXT

            # load the script
            infile = open(fn, 'r')
            # read a line - TODO: add a check for early exit here (maybe)
            scode = infile.read()
            infile.close()

            # parse the script into an AST tree
            ccode = self.__ast.parse(scode)

            # save the current script name
            self.__lastScript = filename
            self.setSysVar_('currentScript', filename)

            # and run the code
            self.__ast.run(ccode)

            # if we're retaining the def funcs() from this script
            if persist:
                newprocs = self.getProcs_()
                if len(newprocs) > 0:
                    for k in newprocs:
                        self.__persistprocs.append(k)

        except Exception as e:
            es = ""
            for e in self.__ast.error:
                t = e.get_error()
                if t is not None:
                    es = str(t[0]) + ": " + str(e.msg)
                else:
                    es = e.msg
                break

            return self.reporterr_("Error loading script '"+filename+"': "+es)

        return None

    # is a script symbol defined?
    def isDef_(self, name):
        """Return True if the symbol is defined.

        Checks the symbol table for a name (either a variable or
        functions) that has been defined by a script.

            Args:

                name    :   The symbol name to check

            Returns:

                True if the name (func or variable) has been defined in a script.

        """

        if not name:
            return False
        # strip off () if it's a proc
        lp = name.find('(')
        if lp >= 0:
            # get the bare symbol name
            key = name[0:lp]
        else:
            key = name

        if key in self.__ast.symtable:
            return True
        return False

    # returns a list of currently-defined def functions
    def listDefs_(self):
        """Returns a list of currently-defined def functions.

        List script-defined functions.  The returned list may be empty
        if no functions have been defined.

            Args:

                None

            Returns:

                A list[] of the function names (if any).

        """

        klist = []
        for k in self.__ast.symtable:
            if type(self.__ast.symtable[k]) == asteval.asteval.Procedure:
                klist.append(k)
        return klist

    # return a system var to the script (read-only to scripts)
    def getSysVar_(self, name, default=None):
        """Returns the value of a system var to the script.

        The engine maintains a table of values that the host application
        can read and write, but the scripts can only read.  This provides
        a useful means of passing system-level info down into the scripts.

        Scripts call this as "getSysVar_()".  The host could call it also,
        if need be.  The vars are set by the host with "setSysVar_()", which
        is NOT exposed to the scripts.

            Args:

                name    :   The name to retrieve.

                default :   A value to return if the name isn't found.

            Returns:

                The value stored under "name", or the default value.

        """
        if not name:
            return default
        try:
            if name not in self.__systemVars:
                return default
            else:
                return self.__systemVars[name]
        except:
            return default

    # returns the value of a script variable to the host program
    def getvar_(self, vname, default=None):
        """Returns the value of a script variable to the host program.

        This method allows the host application to get the value of a
        variable defined in a script.

        Scripts can call this as the "getvar_()" function.  This might
        seem redundant, since a script can just get the value of a
        variable directly.  But this function allows for *indirect*
        referencing, which can be very powerful.  And a nightmare to
        troubleshoot, if not used properly.

            Args:

                vname   :   The name of the script-defined variable.

                default :   Default to return if it's not defined.

            Returns:

                The value of the variable, or the default argument.

        """

        if not vname or len(vname) < 1:
            return False

        ret = self.__ast.getSymbol(vname)
        if not ret:
            return default

        return ret

    # set a script variable from the outside
    # pass None as val to delete
    def setvar_(self, vname, val):
        """Set a variable from the host application.

        This method creates or modifies the value of a variable in
        the script symbol table.  Scripts can then simply reference the
        variable like any other.

        Passing None as the val parameter will remove the variable from
        the symbol table. This might upset some script that depends on that
        variable being defined - use with caution.

        Only user-created vars may be set - that is, those whose names do
        NOT end with "_".  You can use getvar_() to read system-created vars,
        but not set them with setvar_().

        This can also be called by scripts with the "setvar_()" function.
        Again, it allows for indirect variable referencing, which is
        otherwise difficult to do in Python.

            Args:

                vname   :   The name of the script-defined variable.

                val     :   The value to set it to (None to delete it)

            Returns:

                True if success, False otherwise.

        """

        if not vname or len(vname) < 1:
            return False

        # if it's a valid name
        if valid_symbol_name(vname) and not vname.endswith('_'):
            # don't change read-only vars
            if self.__ast.isReadOnly(vname):
                return False
            # if we pass something
            if val is not None:
                # add it to the table
                self.__ast.addSymbol(vname, val)
                return True
            else:
                # otherwise, del any existing copy
                self.__ast.delSymbol(vname)
                return True
        return False

    # stop running the current script and exit gracefully.
    def stop_(self, ret=0):
        """Stop the running script and exit gracefully.

        A script can call "stop_()" to stop execution at the next
        opportunity, and gracefully exit.  A return value may be
        passed back.

            Args:

                ret :   An int returned to the host application.

        """

        # and save the return code where we can get it later
        self.setSysVar_('exitcode_', ret)
        # stop the script from executing
        self.__ast.stoprun()
        return ret

    # exit the engine *and* it's host application abruptly
    def exit_(self, ret=0):
        """Shut it all down right now.

        This method will cause the engine to exit immediately, without
        a clean shutdown.  The script can call "exit_()" to bail out
        right now.

            Args:

                ret :   An int returned as the exit code from the application.

        """

        sys.exit(int(ret))

# ----------------------------------------------------------------------
#
# Support functions
#
# ----------------------------------------------------------------------

#
# return True if the string contains only a-zA-Z0-9-_
# Used as a valid string check on script-supplied file names
# copied from apyshell.support
def checkFileName(fname):
    """Check a file name

    Checks the given filename for characters in the set
    of a-z, A-Z, _ or -

        Args:
            fname   :   The name to check
        Returns:
            True if the name is entirely in that set
            False if there were invalid char(s)

    """

    if not fname or len(fname) < 1 or len(fname) > 256:
        return False

    return all(char in VALIDCHARS for char in fname)

# scan a list of dirs looking for a file
# used by loadScript_()
def findFile(paths, filename):

    if not paths or not filename:
        return None
    if len(paths) == 0 or len(filename) == 0:
        return None

    for dir in paths:
        fn = dir+'/'+filename
        if exists(fn):
            return fn

    return None

# sanitize a file path
# copied from apyshell.support
def sanitizePath(path):
    """Clean a path.

    Remove dangerous characters from a path string.

        Args:

            path    :   The string with the path to clean

        Returns:

            The cleaned path or None if there was a problem

    """

    if not path or len(path) < 1 or len(path) > 4096:
        return None

    #
    # Linux path sanitation
    #

    # strip out \\
    while path and '\\' in path:
        path = path.replace('\\',  '')
    # strip out ..
    while path and '..' in path:
        path = path.replace('..',  '')
    # strip out |
    while path and '|' in path:
        path = path.replace('|',  '')
    while path and ':' in path:
        path = path.replace(':',  '')
    while path[0] == '/':
        path = path[1:]

    np = os.path.normpath(path)
    (p, f) = os.path.split(np)

    path = os.path.join(p, f)

    #
    # Windows - TODO:
    #

    return path


def dump(obj, tag=None):
    print("============================================")
    if tag is not None:
        print("", tag)
    else:
        print("")
    if type(obj) is DictType:
        print(getattr(obj, 'items'))
        for k in obj:
            if type(obj[k]) == asteval.asteval.Procedure:
                print("  {} : {}  {}".format(k, obj[k], type(obj[k])))
    print("=============================================")
