# -----------------------------------------------------------------------------
# calc.py -- a calculator with variables, real numbers, div/mod, and casts.
#
# COS 301 Spring 2026, HW02.  Based on the calc.py example from O'Reilly's
# "Lex and Yacc", p. 63, as distributed with PLY.
#
# Usage:
#     python3 calc.py < input.txt > output.txt
#
# One statement per line is read from standard input.  The value of each
# stand-alone expression is written to standard output and flushed as soon as
# the statement is read; assignments produce no output.  Every diagnostic goes
# to standard error, so standard output contains results and nothing else.
#
# The module is importable without side effects: building the parser and
# reading standard input happen inside build() and main() respectively, so a
# test harness can import this file and drive evaluate() directly.  Running the
# module writes no files: the LALR tables are built in memory.
#
# Grammar:
#     statement  -> name '=' expression
#                 | expression
#     expression -> expression ('+'|'-'|'*'|'/'|'//'|'%') expression
#                 | '-' expression
#                 | '(' expression ')'
#                 | 'real'  '(' expression ')'
#                 | 'floor' '(' expression ')'
#                 | NUMBER
#                 | name
#     name       -> NAME | 'real' | 'floor'
#
# Semantics (see README.md for the reasoning behind each choice):
#   * A binary operator requires both operands to have the same type.  A
#     mismatch prints a line beginning "type error:" to standard error and the
#     expression takes the value 0, as required by the assignment.  Because
#     that 0 is an int, a mismatch nested inside a real-valued expression can
#     flag a second type error; this is a consequence of the specified
#     substitution and is intentional.
#   * An arithmetic fault -- division or modulo by zero, or an overflow in a
#     conversion -- prints a line beginning "math error:" to standard error and
#     the expression takes the zero of the operand's own type (0 or 0.0).
#     Evaluation of the remaining input continues in every case: no input is
#     ever left unread because of a bad statement.
#   * A lexical or syntactic error abandons the rest of the offending line and
#     nothing else; evaluation resumes at the next line of input.
#   * "real" and "floor" are contextual keywords.  Followed by '(' they are
#     conversions; anywhere else they are ordinary variable names.
#
# Provenance:  [Gn] marks AI-assisted code.  The number keys to the "AI usage"
# table in README.md, which records the model, the date, the request, and what
# I verified by hand.  [Gn*] marks AI-generated code that I then edited myself.
# Untagged code is from the original PLY example or is my own.
# -----------------------------------------------------------------------------

import math  # [G1]
import sys  # [G5]

import ply.lex as lex
import ply.yacc as yacc


# [G9] A dedicated exception type, rather than the built-in SyntaxError, so
# that this signal cannot be confused with a SyntaxError raised for any other
# reason anywhere in the call stack.  Raising it abandons exactly one line.
class StatementAbort(Exception):
    """Raised by the lexer or parser to abandon the current input line."""


tokens = ("NAME", "NUMBER", "FLOORDIV", "REAL", "FLOOR")  # [G2] [G3]

literals = ["=", "+", "-", "*", "/", "(", ")", "%"]  # [G2]

# Tokens


# [G7] "real" and "floor" are recognized as distinct token types here so that
# the grammar can tell a conversion from a variable reference, while still
# allowing both words to be used as variable names.
def t_NAME(t):
    r"[a-zA-Z_][a-zA-Z0-9_]*"
    if t.value == "real":
        t.type = "REAL"
    elif t.value == "floor":
        t.type = "FLOOR"
    return t


t_FLOORDIV = r"//"  # [G2]


# [G1] Recognizes decimals and scientific notation and yields a Python float
# for those forms, an int otherwise.  The groups are non-capturing because PLY
# builds one master regex and capturing groups would disturb its indexing.
def t_NUMBER(t):
    r"\d*\.\d+(?:[eE][-+]?\d+)?|\d+\.\d*(?:[eE][-+]?\d+)?|\d+[eE][-+]?\d+|\d+"
    if "." in t.value or "e" in t.value or "E" in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t


t_ignore = " \t"


def t_newline(t):
    r"\n+"
    t.lexer.lineno += t.value.count("\n")


def t_error(t):
    print("Illegal character '%s'" % t.value[0], file=sys.stderr)  # [G5]
    t.lexer.skip(1)
    raise StatementAbort  # [G9] abandon the rest of the line


# Parsing rules

precedence = (
    ("left", "+", "-"),
    ("left", "*", "/", "FLOORDIV", "%"),  # [G2]
    ("right", "UMINUS"),
)

# dictionary of names
names = {}


def p_statement_assign(p):
    """statement : NAME "=" expression
    | REAL "=" expression
    | FLOOR "=" expression"""  # [G7]
    names[p[1]] = p[3]


def p_statement_expr(p):
    "statement : expression"
    print(p[1], flush=True)  # [G5] flush so output appears as soon as it is read


def p_expression_binop(p):
    """expression : expression '+' expression
    | expression '-' expression
    | expression '*' expression
    | expression '/' expression
    | expression FLOORDIV expression
    | expression '%' expression"""  # [G2]
    left, op, right = p[1], p[2], p[3]

    # [G4] Requirement 6: both operands must have the same type.
    if type(left) is not type(right):
        print(
            f"type error: mismatched types {type(left).__name__} "
            f"and {type(right).__name__} for '{op}'",
            file=sys.stderr,
        )
        p[0] = 0
        return

    # [G8] Arithmetic faults are contained here.  Letting ZeroDivisionError or
    # OverflowError escape a production rule terminates the interpreter and
    # discards the rest of the input stream, which the assignment forbids.
    # The substituted value is the zero of the operand type, so that recovering
    # from a math fault does not manufacture a spurious type error higher up.
    zero = type(left)(0)
    try:
        if op == "+":
            p[0] = left + right
        elif op == "-":
            p[0] = left - right
        elif op == "*":
            p[0] = left * right
        elif op == "/":
            p[0] = left / right
        elif op == "//":
            p[0] = left // right
        elif op == "%":
            p[0] = left % right
        else:
            print(f"internal error: unhandled operator '{op}'", file=sys.stderr)
            p[0] = zero
    except ZeroDivisionError:
        print(f"math error: division by zero in '{op}'", file=sys.stderr)
        p[0] = zero
    except (OverflowError, ValueError) as exc:
        print(f"math error: {exc} in '{op}'", file=sys.stderr)
        p[0] = zero


def p_expression_uminus(p):
    "expression : '-' expression %prec UMINUS"
    p[0] = -p[2]


def p_expression_group(p):
    "expression : '(' expression ')'"
    p[0] = p[2]


def p_expression_real(p):
    "expression : REAL '(' expression ')'"  # [G3]
    try:
        p[0] = float(p[3])
    except (OverflowError, ValueError) as exc:  # [G8] e.g. an int too big to be a float
        print(f"math error: real(): {exc}", file=sys.stderr)
        p[0] = 0.0


def p_expression_floor(p):
    "expression : FLOOR '(' expression ')'"  # [G3]
    try:
        p[0] = math.floor(p[3])
    except (OverflowError, ValueError) as exc:  # [G8] e.g. floor(1e400), floor of a nan
        print(f"math error: floor(): {exc}", file=sys.stderr)
        p[0] = 0


def p_expression_number(p):
    "expression : NUMBER"
    p[0] = p[1]


def p_expression_name(p):
    """expression : NAME
    | REAL
    | FLOOR"""  # [G7]
    try:
        p[0] = names[p[1]]
    except LookupError:
        print("Undefined name '%s'" % p[1], file=sys.stderr)  # [G5]
        p[0] = 0


def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value, file=sys.stderr)  # [G5]
    else:
        print("Syntax error at EOF", file=sys.stderr)  # [G5]
    raise StatementAbort  # [G9] abandon the rest of the line


# [G9] Construction and the read-eval loop live in functions so that importing
# this module has no side effects.  lex.lex() and yacc.yacc() still find the
# t_/p_ rules above because PLY reads the calling frame's module globals.
def build():
    """Build and return the (lexer, parser) pair for the calculator language.

    The LALR tables are built in memory: write_tables=False keeps parsetab.py
    out of the working directory and debug=False keeps parser.out out of it,
    so the program runs unchanged from a read-only directory.  Grammar
    warnings and conflicts are still reported on standard error.
    """
    return lex.lex(), yacc.yacc(debug=False, write_tables=False)


def evaluate(source, parser, lexer):
    """Evaluate one statement, printing its value and any diagnostics.

    Every failure mode is contained: a lexical or syntactic error abandons
    this statement only, and any other exception escaping a production rule is
    reported rather than allowed to terminate the program.
    """
    try:
        parser.parse(source, lexer=lexer)
    except StatementAbort:  # [G9] this line is abandoned; the next one is not
        pass
    except Exception as exc:  # [G8] last resort: never stop reading input
        print(f"internal error: {exc}", file=sys.stderr)


def main():
    """Read statements from standard input until end of file."""
    lexer, parser = build()
    while True:
        try:
            line = input()  # [G5] no prompt: standard output carries results only
        except EOFError:
            break
        if not line:
            continue
        evaluate(line, parser, lexer)
    return 0


if __name__ == "__main__":
    sys.exit(main())