# -----------------------------------------------------------------------------
# calc.py
#
# A simple calculator with variables.   This is from O'Reilly's
# "Lex and Yacc", p. 63.
# Extended to support real numbers and scientific notation. # [G]
# Extended to support div (//) and mod (%). # [G]
# Extended to support real() casting. # [G]
# Extended to support floor() casting. # [G]
# Modified to strictly separate stdout results and stderr diagnostics. # [G]
# -----------------------------------------------------------------------------

import math # [G]
import sys  # [G]

tokens = (
    'NAME', 'NUMBER', 'FLOORDIV', 'REAL', 'FLOOR' # [G]
)

literals = ['=', '+', '-', '*', '/', '(', ')', '%'] # [G]

# Tokens

def t_NAME(t): # [G]
    r'[a-zA-Z_][a-zA-Z0-9_]*' # [G]
    if t.value == 'real': # [G]
        t.type = 'REAL' # [G]
    elif t.value == 'floor': # [G]
        t.type = 'FLOOR' # [G]
    return t # [G]

t_FLOORDIV = r'//' # [G]


def t_NUMBER(t):
    r'\d*\.\d+(?:[eE][-+]?\d+)?|\d+\.\d*(?:[eE][-+]?\d+)?|\d+[eE][-+]?\d+|\d+' # [G]
    if '.' in t.value or 'e' in t.value or 'E' in t.value: # [G]
        t.value = float(t.value) # [G]
    else: # [G]
        t.value = int(t.value) # [G]
    return t

t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    print("Illegal character '%s'" % t.value[0], file=sys.stderr) # [G]
    t.lexer.skip(1)

# Build the lexer
import ply.lex as lex
lexer = lex.lex()

# Parsing rules

precedence = (
    ('left', '+', '-'),
    ('left', '*', '/', 'FLOORDIV', '%'), # [G]
    ('right', 'UMINUS'),
)

# dictionary of names
names = {}

def p_statement_assign(p):
    'statement : NAME "=" expression'
    names[p[1]] = p[3]


def p_statement_expr(p):
    'statement : expression'
    print(p[1]) # This remains unchanged because it is an evaluation result


def p_expression_binop(p):
    '''expression : expression '+' expression
                  | expression '-' expression
                  | expression '*' expression
                  | expression '/' expression
                  | expression FLOORDIV expression
                  | expression '%' expression'''
    # Note: FLOORDIV and '%' grammar rules were added to the docstring above # [G]
    if p[2] == '+':
        p[0] = p[1] + p[3]
    elif p[2] == '-':
        p[0] = p[1] - p[3]
    elif p[2] == '*':
        p[0] = p[1] * p[3]
    elif p[2] == '/':
        p[0] = p[1] / p[3]
    elif p[2] == '//': # [G]
        p[0] = p[1] // p[3] # [G]
    elif p[2] == '%': # [G]
        p[0] = p[1] % p[3] # [G]


def p_expression_uminus(p):
    "expression : '-' expression %prec UMINUS"
    p[0] = -p[2]


def p_expression_group(p):
    "expression : '(' expression ')'"
    p[0] = p[2]


def p_expression_real(p): # [G]
    "expression : REAL '(' expression ')'" # [G]
    p[0] = float(p[3]) # [G]


def p_expression_floor(p): # [G]
    "expression : FLOOR '(' expression ')'" # [G]
    p[0] = math.floor(p[3]) # [G]


def p_expression_number(p):
    "expression : NUMBER"
    p[0] = p[1]


def p_expression_name(p):
    "expression : NAME"
    try:
        p[0] = names[p[1]]
    except LookupError:
        print("Undefined name '%s'" % p[1], file=sys.stderr) # [G]
        p[0] = 0


def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value, file=sys.stderr) # [G]
    else:
        print("Syntax error at EOF", file=sys.stderr) # [G]

import ply.yacc as yacc
parser = yacc.yacc()

while True:
    try:
        s = input() # [G] Removed the 'calc > ' prompt string
    except EOFError:
        break
    if not s:
        continue
    yacc.parse(s)