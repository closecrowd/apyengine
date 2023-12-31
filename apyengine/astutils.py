#!/usr/bin/env python3
"""astutils - utility functions for asteval

Credits:
    * version: 1.0.0
    * last update: 2023-Dec-203
    * License:  MIT
    * Author:  Mark Anacker <closecrowd@pm.me>
    * Copyright (c) 2023 by Mark Anacker

Note:
    Originally by: Matthew Newville, The University of Chicago, <newville@cars.uchicago.edu>

"""

from __future__ import division, print_function
import re
import ast

from sys import exc_info
import importlib

##############################################################################

#
# Globals
#

MAX_EXPONENT = 10000
MAX_STR_LEN = 2 << 17  # 256KiB
MAX_SHIFT = 1000
MAX_OPEN_BUFFER = 2 << 17

RESERVED_WORDS = ('and', 'as', 'assert', 'break', 'class', 'continue',
                  'def', 'del', 'elif', 'else', 'except', 'exec',
                  'finally', 'for', 'from', 'global', 'if', 'import',
                  'in', 'is', 'lambda', 'not', 'or', 'pass', 'print',
                  'raise', 'return', 'try', 'while', 'with', 'True',
                  'False', 'None', 'eval', 'execfile', '__import__',
                  '__package__')

NAME_MATCH = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*$").match

UNSAFE_ATTRS = ('__subclasses__', '__bases__', '__globals__', '__code__',
                '__closure__', '__func__', '__self__', '__module__',
                '__dict__', '__class__', '__call__', '__get__',
                '__getattribute__', '__subclasshook__', '__new__',
                '__init__', 'func_globals', 'func_code', 'func_closure',
                'im_class', 'im_func', 'im_self', 'gi_code', 'gi_frame',
                '__asteval__', 'f_locals', '__mro__', '__builtins__', '__doc__')

# inherit these from python's __builtins__
FROM_PY = ('ArithmeticError', 'AssertionError', 'AttributeError',
           'BaseException', 'BufferError', 'BytesWarning',
           'DeprecationWarning', 'EOFError', 'EnvironmentError',
           'Exception', 'False', 'FloatingPointError', 'GeneratorExit',
           'IOError', 'ImportError', 'ImportWarning', 'IndentationError',
           'IndexError', 'KeyError', 'KeyboardInterrupt', 'LookupError',
           'MemoryError', 'NameError', 'None',
           'NotImplementedError', 'OSError', 'OverflowError',
           'ReferenceError', 'RuntimeError', 'RuntimeWarning',
           'StopIteration', 'SyntaxError', 'SyntaxWarning', 'SystemError',
           'SystemExit', 'True', 'TypeError', 'TimeoutExpired', 'UnboundLocalError',
           'UnicodeDecodeError', 'UnicodeEncodeError', 'UnicodeError',
           'UnicodeTranslateError', 'UnicodeWarning', 'ValueError',
           'Warning', 'ZeroDivisionError', 'abs', 'all', 'any', 'bin',
           'bool', 'bytearray', 'bytes', 'chr', 'complex', 'decode', 'dict', 'dir',
           'divmod', 'encode', 'enumerate', 'filter', 'float', 'format', 'frozenset',
           'hash', 'hex', 'id', 'input', 'int', 'isinstance', 'len', 'list', 'map',
           'max', 'min', 'oct', 'ord', 'pow', 'range', 'repr',
           'reversed', 'round', 'set', 'slice', 'sorted', 'str', 'sum',
           'tuple', 'zip')

# inherit these from python's math
# these symbols will have _ appended
FROM_MATH = ('acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2', 'atanh',
             'ceil', 'copysign', 'cos', 'cosh', 'degrees', 'e', 'exp',
             'fabs', 'factorial', 'floor', 'fmod', 'frexp', 'fsum',
             'gamma', 'lgamma', 'gcd', 'log2', 'isfinite', 'isclose',
             'hypot', 'inf', 'isinf', 'isnan', 'ldexp', 'log', 'log10', 'log1p',
             'modf', 'nan', 'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan',
             'tanh', 'trunc')

# inherit from numpy
# these symbols will have _ appended
FROM_NUMPY = ('Inf', 'NAN', 'abs', 'add', 'alen', 'all', 'amax', 'amin',
              'angle', 'any', 'append', 'arange', 'arccos', 'arccosh',
              'arcsin', 'arcsinh', 'arctan', 'arctan2', 'arctanh',
              'argmax', 'argmin', 'argsort', 'argwhere', 'around', 'array',
              'array2string', 'asanyarray', 'asarray', 'asarray_chkfinite',
              'ascontiguousarray', 'asfarray', 'asfortranarray',
              'asmatrix', 'asscalar', 'atleast_1d', 'atleast_2d',
              'atleast_3d', 'average', 'bartlett', 'base_repr',
              'bitwise_and', 'bitwise_not', 'bitwise_or', 'bitwise_xor',
              'blackman', 'bool', 'broadcast', 'broadcast_arrays', 'byte',
              'c_', 'cdouble', 'ceil', 'cfloat', 'chararray', 'choose',
              'clip', 'clongdouble', 'clongfloat', 'column_stack',
              'common_type', 'complex', 'complex128', 'complex64',
              'complex_', 'complexfloating', 'compress', 'concatenate',
              'conjugate', 'convolve', 'copy', 'copysign', 'corrcoef',
              'correlate', 'cos', 'cosh', 'cov', 'cross', 'csingle',
              'cumprod', 'cumsum', 'datetime_data', 'deg2rad', 'degrees',
              'delete', 'diag', 'diag_indices', 'diag_indices_from',
              'diagflat', 'diagonal', 'diff', 'digitize', 'divide', 'dot',
              'double', 'dsplit', 'dstack', 'dtype', 'e', 'ediff1d',
              'empty', 'empty_like', 'equal', 'exp', 'exp2', 'expand_dims',
              'expm1', 'extract', 'eye', 'fabs', 'fill_diagonal', 'finfo',
              'fix', 'flatiter', 'flatnonzero', 'fliplr', 'flipud',
              'float', 'float32', 'float64', 'float_', 'floating', 'floor',
              'floor_divide', 'fmax', 'fmin', 'fmod', 'format_parser',
              'frexp', 'frombuffer', 'fromfile', 'fromfunction',
              'fromiter', 'frompyfunc', 'fromregex', 'fromstring', 'fv',
              'genfromtxt', 'getbufsize', 'geterr', 'gradient', 'greater',
              'greater_equal', 'hamming', 'hanning', 'histogram',
              'histogram2d', 'histogramdd', 'hsplit', 'hstack', 'hypot',
              'i0', 'identity', 'iinfo', 'imag', 'in1d', 'index_exp',
              'indices', 'inexact', 'inf', 'info', 'infty', 'inner',
              'insert', 'int', 'int0', 'int16', 'int32', 'int64', 'int8',
              'int_', 'int_asbuffer', 'intc', 'integer', 'interp',
              'intersect1d', 'intp', 'invert', 'ipmt', 'irr', 'iscomplex',
              'iscomplexobj', 'isfinite', 'isfortran', 'isinf', 'isnan',
              'isneginf', 'isposinf', 'isreal', 'isrealobj', 'isscalar',
              'issctype', 'iterable', 'ix_', 'kaiser', 'kron', 'ldexp',
              'left_shift', 'less', 'less_equal', 'linspace',
              'little_endian', 'load', 'loads', 'loadtxt', 'log', 'log10',
              'log1p', 'log2', 'logaddexp', 'logaddexp2', 'logical_and',
              'logical_not', 'logical_or', 'logical_xor', 'logspace',
              'long', 'longcomplex', 'longdouble', 'longfloat', 'longlong',
              'mafromtxt', 'mask_indices', 'mat', 'matrix',
              'maximum', 'maximum_sctype', 'may_share_memory', 'mean',
              'median', 'memmap', 'meshgrid', 'mgrid', 'minimum',
              'mintypecode', 'mirr', 'mod', 'modf', 'msort', 'multiply',
              'nan', 'nan_to_num', 'nanargmax', 'nanargmin', 'nanmax',
              'nanmin', 'nansum', 'ndarray', 'ndenumerate', 'ndfromtxt',
              'ndim', 'ndindex', 'negative', 'newaxis', 'nextafter',
              'nonzero', 'not_equal', 'nper', 'npv', 'number',
              'obj2sctype', 'ogrid', 'ones', 'ones_like', 'outer',
              'packbits', 'percentile', 'pi', 'piecewise', 'place', 'pmt',
              'poly', 'poly1d', 'polyadd', 'polyder', 'polydiv', 'polyfit',
              'polyint', 'polymul', 'polysub', 'polyval', 'power', 'ppmt',
              'prod', 'product', 'ptp', 'put', 'putmask', 'pv', 'r_',
              'rad2deg', 'radians', 'rank', 'rate', 'ravel', 'real',
              'real_if_close', 'reciprocal', 'record', 'remainder',
              'repeat', 'reshape', 'resize', 'restoredot', 'right_shift',
              'rint', 'roll', 'rollaxis', 'roots', 'rot90', 'round',
              'round_', 'row_stack', 's_', 'sctype2char', 'searchsorted',
              'select', 'setbufsize', 'setdiff1d', 'seterr', 'setxor1d',
              'shape', 'short', 'sign', 'signbit', 'signedinteger', 'sin',
              'sinc', 'single', 'singlecomplex', 'sinh', 'size',
              'sometrue', 'sort', 'sort_complex', 'spacing', 'split',
              'sqrt', 'square', 'squeeze', 'std', 'str', 'str_',
              'subtract', 'sum', 'swapaxes', 'take', 'tan', 'tanh',
              'tensordot', 'tile', 'trace', 'transpose', 'trapz', 'tri',
              'tril', 'tril_indices', 'tril_indices_from', 'trim_zeros',
              'triu', 'triu_indices', 'triu_indices_from', 'true_divide',
              'trunc', 'ubyte', 'uint', 'uint0', 'uint16', 'uint32',
              'uint64', 'uint8', 'uintc', 'uintp', 'ulonglong', 'union1d',
              'unique', 'unravel_index', 'unsignedinteger', 'unwrap',
              'ushort', 'vander', 'var', 'vdot', 'vectorize', 'vsplit',
              'vstack', 'where', 'who', 'zeros', 'zeros_like',
              'fft', 'linalg', 'polynomial', 'random')

# Python time module
# these symbols will have _ appended
FROM_TIME = ('ctime', 'clock', 'altzone', 'asctime', 'strptime',
              'gmtime', 'mktime', 'timezone', 'sleep', 'tzname', 'daylight',
              'time', 'strftime', 'localtime', 'monotonic' )

# Python base64 module
# these symbols will have _ appended
FROM_BASE64 = ('b64encode', 'b64decode', 'urlsafe_b64encode', 'urlsafe_b64decode')

# Python JSON module
# these symbols will have _ appended
FROM_JSON = ('dumps', 'loads', 'JSONDecoder', 'JSONEncoder')
# rename theses a bit to dodge a conflict with numpy
JSON_RENAMES = { 'dumps': 'jsondumps', 'loads': 'jsonloads' }

# Python re module
FROM_RE = {'compile', 'search', 'match', 'fullmatch', 'split', 'findall',
            'finditer', 'sub', 'subn', 'escape', 'purge', 'error', 'ASCII', 'IGNORECASE',
           'LOCALE', 'MULTILINE', 'NOFLAG', 'DOTALL', 'UNICODE', 'VERBOSE', 'DEBUG' }

# python modules that may be installed by scripts with the install_() function
# and their symbols (defined above)
# The 'python' module is automatically installed
MODULE_LIST = {'python': FROM_PY, 'math': FROM_MATH, 'time': FROM_TIME,
                'numpy': FROM_NUMPY, 'base64': FROM_BASE64, 'json': FROM_JSON,
                're': FROM_RE}

##############################################################################

# replacement for type()
def type_(obj, *varargs, **varkws):
    """type that prevents varargs and varkws"""
    return type(obj).__name__

# replacement for string.split()
def split_(s, str="", num=0):
    """replacement for string split()"""
    if num != 0:
        return s.split(str, num)
    else:
        return s.split(str)

# case-insensitive string compare
def strcasecmp_(s1, s2):
    """case-insensitive string compare"""
    return (s1.casefold() == s2.casefold())

# rename Python funcs
LOCALFUNCS = {'type': type_, 'split': split_, 'strcasecmp': strcasecmp_}

# Safe versions of functions to prevent denial of service issues

def safe_pow(base, exp):
    """safe version of pow"""
    if exp > MAX_EXPONENT:
        raise RuntimeError("Invalid exponent, max exponent is {}".format(MAX_EXPONENT))
    return base ** exp

def safe_mult(a, b):
    """safe version of multiply"""
    if isinstance(a, str) and isinstance(b, int) and len(a) * b > MAX_STR_LEN:
        raise RuntimeError("String length exceeded, max string length is {}".format(MAX_STR_LEN))
    return a * b

def safe_add(a, b):
    """safe version of add"""
    if isinstance(a, str) and isinstance(b, str) and len(a) + len(b) > MAX_STR_LEN:
        raise RuntimeError("String length exceeded, max string length is {}".format(MAX_STR_LEN))
    return a + b

def safe_lshift(a, b):
    """safe version of lshift"""
    if b > MAX_SHIFT:
        raise RuntimeError("Invalid left shift, max left shift is {}".format(MAX_SHIFT))
    return a << b


OPERATORS = {ast.Is: lambda a, b: a is b,
             ast.IsNot: lambda a, b: a is not b,
             ast.In: lambda a, b: a in b,
             ast.NotIn: lambda a, b: a not in b,
             ast.Add: safe_add,
             ast.BitAnd: lambda a, b: a & b,
             ast.BitOr: lambda a, b: a | b,
             ast.BitXor: lambda a, b: a ^ b,
             ast.Div: lambda a, b: a / b,
             ast.FloorDiv: lambda a, b: a // b,
             ast.LShift: safe_lshift,
             ast.RShift: lambda a, b: a >> b,
             ast.Mult: safe_mult,
             ast.Pow: safe_pow,
             ast.Sub: lambda a, b: a - b,
             ast.Mod: lambda a, b: a % b,
             ast.And: lambda a, b: a and b,
             ast.Or: lambda a, b: a or b,
             ast.Eq: lambda a, b: a == b,
             ast.Gt: lambda a, b: a > b,
             ast.GtE: lambda a, b: a >= b,
             ast.Lt: lambda a, b: a < b,
             ast.LtE: lambda a, b: a <= b,
             ast.NotEq: lambda a, b: a != b,
             ast.Invert: lambda a: ~a,
             ast.Not: lambda a: not a,
             ast.UAdd: lambda a: +a,
             ast.USub: lambda a: -a}


def valid_symbol_name(name):
    """Determine whether the input symbol name is a valid name.

    This checks for Python reserved words, and that the name matches
    the regular expression ``[a-zA-Z_][a-zA-Z0-9_]``

        Args:

          name  :   name to check for validity.

        Returns:

          valid :   True if a name is a valid symbol name

    """

    if name in RESERVED_WORDS:
        return False
    return NAME_MATCH(name) is not None


def op2func(op):
    """Return function for operator nodes."""

    return OPERATORS[op.__class__]


class Empty:
    """Empty class.

    This class is used as a return value in the __call__() and
    on_return() methods in asteval.Interpreter.  If differentiates
    between an empty return and one with an expression.

    """

    def __init__(self):
        """TODO: docstring in public method."""
        pass

    def __nonzero__(self):
        """TODO: docstring in magic method."""
        return False

# Set the global value to the return sentinel
ReturnedNone = Empty()


class ExceptionHolder(object):
    """Exception handler support.

    This class carries the info needed to properly route and
    handle exceptions.  It's generally called from on_raise() in
    asteval.py

    """

    def __init__(self, node, exc=None, msg='', expr=None, lineno=0):
        """Create a new Exception report object

        Holds some exception metadata.

            Args:

                node    :   Node that had an exception
                exc     :   The exception
                msg     :   Error message
                expr    :   Expression that caused the exception
                lineno  :   Source file line numner

        """

        self.node = node
        self.expr = expr
        self.msg = msg
        self.exc = exc
        self.lineno = lineno
        self.exc_info = exc_info()

        if self.exc is None and self.exc_info[0] is not None:
            self.exc = self.exc_info[0]
        if self.msg == '' and self.exc_info[1] is not None:
            self.msg = self.exc_info[1]

    def get_error(self):
        """Retrieve error data."""
        col_offset = -1
        if self.node is not None:
            try:
                col_offset = self.node.col_offset
            except AttributeError:
                pass
        try:
            exc_name = self.exc.__name__
        except AttributeError:
            exc_name = str(self.exc)
        if exc_name in (None, 'None'):
            exc_name = 'UnknownError'

        out = ["   %s" % self.expr]
        if col_offset > 0:
            out.append("    %s^^^" % ((col_offset)*' '))

        out.append(str(self.msg))
        return (exc_name, '\n'.join(out))


class NameFinder(ast.NodeVisitor):
    """Find all symbol names used by a parsed node.

    """

    def __init__(self):
        """TODO: docstring in public method.
        """

        self.names = []
        ast.NodeVisitor.__init__(self)

    def generic_visit(self, node):
        """TODO: docstring in public method.
        """

        if node.__class__.__name__ == 'Name':
            if node.ctx.__class__ == ast.Load and node.id not in self.names:
                self.names.append(node.id)
        ast.NodeVisitor.generic_visit(self, node)


# grab the Python built-in symbols
builtins = __builtins__
if not isinstance(builtins, dict):
    builtins = builtins.__dict__


def get_ast_names(astnode):
    """Return symbol Names from an AST node."""

    finder = NameFinder()
    finder.generic_visit(astnode)
    return finder.names


def make_symbol_table(modlist, **kwargs):

    """Create a default symbol table

    This function creates the default symbol table, and installs some pre-defined
    symbols.

        Args:

            modlist : list names of currently-installed modules
            **kwargs :  optional additional symbol name, value pairs to include in symbol table

        Returns:

            symbol_table : dict a symbol table that can be used in `asteval.Interpereter`

    """

    symtable = {}

    # by default, we only install the Python built-ins
    # and these do NOT get an '_' appended
    install_python_module(symtable, 'python', modlist, False)

    # install the special over-ride functions
    symtable.update(LOCALFUNCS)

    # add the passed-in symbols (if any)
    symtable.update(kwargs)

    return symtable

# install one of the pre-defined modules into the engine
# as if: import * from <module>
#
# scripts call this as install_('modname')
#
def install_python_module(symtable, modname, modlist, rename=True):
    """Install a pre-defined Python module.

    This function will install one of the Python modules (listed in MODULE_LIST)
    directly into the symbol table.  Some of the functions in the modules are
    renamed to prevent conflicts with other modules.  Once installed, they can
    not be uninstalled during this run of apyshell.

    This is called by the install() function in asteval.py

        Args:

            symtable    :   The symbol table to install into.
            modname     :   The module name to install.
            modlist     :   A list of currently-installed modules.
            rename      :   If True, add an '_' to each function name.

        Returns:

            The return value. True for success, False otherwise.

    """

    # make sure this is an approved module
    if modname not in MODULE_LIST:
        return False

    # check the list of installed modules and make sure this one
    # isn't already installed
    if modname in modlist:
        return False

    # make a temp symbol table
    lst = {}
    # get the allowed symbol list for the selected module
    md = MODULE_LIST[modname]

    # rename some module functions to match our convention

    try:
        # if not python, go and import the module
        # ('python' is installed at init time)
        if modname != 'python':
            mod = importlib.import_module(modname)
            modd = mod.__dict__
        else:
            # we don't have to import the builtins
            modd = builtins
        # walk the symbols in the new module, adding only the safe
        # symbols to the script table
        for k in modd:
            # if they're on the approved list
            if k in md:
                # if this module is flagged for rename:
                if rename:
                    # json has some special names
                    if modname == 'json':
                        if k in JSON_RENAMES:
                            # JSON renamed symbols
                            sym = JSON_RENAMES[k]+'_'
                        else:
                            # JSON not renamed
                            sym = k+'_'
                    # re gets ALL syms renamed
                    elif modname == 're':
                        sym = 're'+k+'_'
                    else:
                        # by default, add the _
                        sym = k+'_'
                else:
                    # symbol not modified
                    sym = k
                # add to the temp table
                lst[sym] = modd[k]

        # and add the new symbols to the passed-in table
        symtable.update(lst)

        # add the module name to the list (except 'python')
        # it's in there by default, so render it invisible to the
        # listModules_() function.
        if modname != 'python':
            modlist.append(modname)

        return True

    except ImportError as e:
        # failed to import the module
        print(str(e))

    return False
