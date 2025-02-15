#!/usr/bin/env -S uv run -q
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "dnspython==2.6.1",
#     "lark==1.2.2",
#     "typer-slim==0.12.5",
# ]
# ///
import logging
import os
import re
import sys
import time

DNS_SUFFIX = os.environ.get('DNS_SUFFIX', '.example.com.') # operational data provided by USCYBERCOM

eval = None # safety

# logging
logger = logging.getLogger('thrower')
logger.setLevel(logging.getLevelName('DEBUG'))
h = logging.StreamHandler()
h.setFormatter(logging.Formatter(
    "%(name)s: %(asctime)s | %(levelname)-7s | %(filename)s:%(lineno)-4s :: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
))
logger.addHandler(h)

# 3rd party
try:
    from lark import Lark
    import dns.resolver
except ImportError as _e:
    print(_e)
    print("Install uv, then run with ./thrower.py run program.txt")
    sys.exit(1)

# syntax

grammar = """
    start: instruction_list
    instruction_list: instruction+
    code_block: "{" instruction_list "}"

    COMMENT: /#.*/

    string_lit: /".*"/
    int_lit: NUMBER
    lit: string_lit | int_lit

    reg: "r" int_lit
    rval: reg | lit

    resolve_arg: rval

    instruction: "resolve" resolve_arg         -> resolve
               | "sleep"   NUMBER              -> sleep
               | "repeat"  NUMBER code_block   -> repeat
               | "load"    reg                 -> load
               | "store"   reg                 -> store
               | "if" reg "==" rval code_block -> ifeq
               | "if" reg "!=" rval code_block -> ifne
               | "assert" reg "==" rval        -> assert_eq
               | "assert" reg "!=" rval        -> assert_ne

    %import common.LETTER
    %import common.INT -> NUMBER
    %import common.WS
    %ignore WS
    %ignore COMMENT
"""

PARSER = Lark(grammar, propagate_positions=True)

# Interpreter

class InterpreterException(Exception):
    def __init__(self, t, message=None):
        super().__init__(message)
        self.t = t
        self.message = message

class RuleNotImplementedError(InterpreterException): pass
class StopException(InterpreterException): pass
class BudgetException(StopException): pass
class AssertionException(StopException): pass

class Interpreter:
    count: int = 0

    def __init__(self):
        self.setup_logger()

    def setup_logger(self):
        Interpreter.count += 1
        self.logger = logging.getLogger('interpreter[%d]' % Interpreter.count)
        self.logger.setLevel(logging.root.level) # same as global
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(
            "%(name)s: %(asctime)s | %(levelname)-7s | %(filename)s:%(lineno)-4s :: %(line)-2s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        ))
        self.logger.addHandler(h)

    def eval(self, t):
        fn = f'eval_{t.data}'
        f = getattr(self, fn, None)
        if f is None: raise RuleNotImplementedError(t)
        return f(t)

class BudgetInterpreter(Interpreter):
    from collections import namedtuple
    Budget = namedtuple('Budget', ['remaining_compute', 'deadline'])

    def __init__(self, budget):
        super().__init__()
        self.budget = budget

    def eval(self, t):
        # check budget
        # defaults
        compute = 1
        ms = 10
        # try custom budget
        budget_fn = f'budget_{t.data}'
        f = getattr(self, budget_fn, None)
        if f is not None:
            compute, ms = f(t)
        remaining_compute = self.budget.remaining_compute - compute
        over_compute = remaining_compute < 0
        end_time = time.time() + (ms/1000)
        over_time = self.budget.deadline < end_time
        if over_compute or over_time:
            raise BudgetException(t=t)
        self.budget = self.budget._replace(remaining_compute=remaining_compute)
        # do it
        return super().eval(t)

class ThrowerInterpreter(BudgetInterpreter):
    def __init__(self, budget, target_ip, target_port):
        super().__init__(budget)
        self.target_ip = target_ip
        self.target_port = target_port
        self.STATE = {}

    def eval_start(self, t):
        assert len(t.children) == 1
        return self.eval(t.children[0])

    def eval_instruction_list(self, t):
        for inst in t.children:
            self.STATE['last'] = self.eval_instruction(inst)

    def eval_string_lit(self, t):
        s = t.children[0].value[1:-1]
        self.logger.debug(f'string: {s!r}', extra=dict(line=t.meta.line))
        return s

    def eval_int_lit(self, t):
        return int(t.children[0])

    def eval_lit(self, t):
        return self.eval(t.children[0])

    def eval_reg(self, t):
        STATE = self.STATE
        rnum = self.eval(t.children[0])
        return (STATE, rnum)

    def eval_resolve_arg(self, t):
        return self.eval(t.children[0])

    def budget_sleep(self, t):
        ms = int(t.children[0]) # sleep time
        if ms < 0: raise StopException(t=t, message="negative sleep time")
        compute = 0
        return compute, ms

    def eval_sleep(self, t):
        ms = int(t.children[0])
        if ms < 0: raise StopException(t=t, message="negative sleep time")
        return self._sleep(ms, t.meta.line)

    def _sleep(self, ms, line):
        self.logger.debug(f'sleeping for {ms}ms', extra=dict(line=line))
        time.sleep(ms/1000)
        return ms

    def budget_resolve(self, t):
        compute = 10
        ms = 5000 # could take up to 5s (source for timeout too)
        return compute, ms

    def eval_resolve(self, t):
        arg = self.eval(t.children[0])
        return self._resolve(arg, t)

    def _resolve(self, domain, t):
        resolver = dns.resolver.Resolver(configure=False)
        resolver.domain = 'localhost.localhost'
        resolver.nameservers = [self.target_ip]
        resolver.nameserver_ports = {self.target_ip: self.target_port}
        resolver.timeout = self.budget_resolve(None)[1]//1000 # seconds
        try:
            response =  resolver.resolve(str(domain) + DNS_SUFFIX, rdtype='A', raise_on_no_answer=False).response
            answer = None
            for section in response.sections:
                for rrset in section:
                    for _answer in rrset:
                        try:
                            answer = _answer.address
                            break
                        except: pass
            if answer is None: raise dns.resolver.NoAnswer
        except dns.resolver.LifetimeTimeout:
            answer = ''
        except dns.resolver.NXDOMAIN:
            answer = ''
        except dns.resolver.NoAnswer:
            answer = ''
        except dns.resolver.NoNameservers:
            answer = ''
        except Exception as e:
            raise StopException(t=t, message="resolver exception: " + repr(e))
        self.logger.debug(f"resolve({domain!r}): {answer!r}", extra=dict(line=t.meta.line))
        return answer

    def eval_load(self, t):
        reg = self.eval(t.children[0])
        state, index = reg
        if index not in state:
            raise StopException(t=t, message=f"uninitialized register: r{index}")
        v = state[index]
        self.logger.debug(f'r{index}: {v!r}', extra=dict(line=t.meta.line))
        return v

    def eval_store(self, t):
        reg = self.eval(t.children[0])
        state, index = reg
        if 'last' not in state:
            raise StopException(t=t)
        v = state['last']
        state[index] = v
        self.logger.debug(f'r{index}:= {v!r}', extra=dict(line=t.meta.line))
        return v

    def eval_rval(self, t):
#        import pdb; pdb.set_trace()
        c = t.children[0]
        if c.data.value == 'lit':
            v = self.eval(t.children[0])
            self.logger.debug(f'rval: {v!r}', extra=dict(line=t.meta.line))
            return v
        elif c.data.value == 'reg':
            reg = self.eval(t.children[0])
            _, index = reg
            self.logger.debug(f'rval: r{index}', extra=dict(line=t.meta.line))
            v = self.eval_load(t) # do the same thing a load does, arg in the right place
            return v
        else:
            assert False, 'rule mismatch'

    def eval_ifeq(self, t):
        reg = self.eval(t.children[0])
        val = self.eval(t.children[1])
        body = t.children[2]
        _, index = reg
        lval = self.eval_load(t) # do the same thing a load does, arg in the right place
        cond = lval == val
        self.logger.debug(f'ifeq: r{reg[1]!r} ({lval!r}) == {val!r} : {cond!r}', extra=dict(line=t.meta.line))
        if cond:
            return self.eval(body)
        else:
            return ''

    def eval_ifne(self, t):
        reg = self.eval(t.children[0])
        val = self.eval(t.children[1])
        body = t.children[2]
        _, index = reg
        lval = self.eval_load(t) # do the same thing a load does, arg in the right place
        cond = lval != val
        self.logger.debug(f'ifne: r{reg[1]!r} ({lval!r}) != {val!r} : {cond!r}', extra=dict(line=t.meta.line))
        if cond:
            return self.eval(body)
        else:
            return ''

    def eval_assert_eq(self, t):
        reg = self.eval(t.children[0])
        val = self.eval(t.children[1])
        _, index = reg
        lval = self.eval_load(t) # do the same thing a load does, arg in the right place
        cond = lval == val
        self.logger.debug(f'assert: r{index} ({lval!r}) == {val!r} : {cond!r}', extra=dict(line=t.meta.line))
        if not cond:
            raise AssertionException(t=t)

    def eval_assert_ne(self, t):
        reg = self.eval(t.children[0])
        val = self.eval(t.children[1])
        _, index = reg
        lval = self.eval_load(t) # do the same thing a load does, arg in the right place
        cond = lval != val
        self.logger.debug(f'assert: r{index} ({lval!r}) != {val!r} : {cond!r}', extra=dict(line=t.meta.line))
        if not cond:
            raise AssertionException(t=t)

    def eval_repeat(self, t):
        count, block = t.children
        c = int(count)
        last = None
        for i in range(c):
            self.logger.debug(f'repeat: {i} < {c}', extra=dict(line=t.meta.line))
            last = self.eval(block)
        return last

    def eval_code_block(self, t):
        assert len(t.children) == 1
        return self.eval(t.children[0])

    def eval_instruction(self, t):
        return self.eval(t)



def run_program(source, target, budget=None):
    if budget is None:
        budget = ThrowerInterpreter.Budget(remaining_compute=1000, deadline=(time.time()+(60*15))) # default 1000 evals (~200 inst.), 15 minutes

    try:
        parse_tree = PARSER.parse(source)
    except:
        logger.exception("Parser Error", extra=dict(line=0))
        sys.exit(13)

    M = re.match(r'(\d+\.\d+\.\d+\.\d+):(\d+)', target)
    if not M:
        raise Exception("Bad Target")
    target_ip = M.group(1)
    target_port = int(M.group(2))

    try:
        I = ThrowerInterpreter(budget, target_ip, target_port)
        I.eval(parse_tree)
    except BudgetException as e:
        logger.error("Budget Overflow at line %d", e.t.meta.line, extra=dict(line=e.t.meta.line))
        sys.exit(11)
    except AssertionException as e:
        logger.error("Assertion Error at line %d", e.t.meta.line, extra=dict(line=e.t.meta.line))
        sys.exit(10)
    except StopException as e:
        logger.error("Error at line %d: %s", e.t.meta.line, e.message, extra=dict(line=e.t.meta.line))
        sys.exit(12)
    except:
        logger.exception("Unexpected Error", extra=dict(line=0))
        sys.exit(1)

def cli():
    import typer
    app = typer.Typer()

    @app.command()
    def test():
        text = """
            sleep 500
            repeat 2 {
                resolve "foo"
                store r1
#               sleep 1000
                if r1 == "127.0.0.1" {
                    resolve "bar"
                    store r2
                    if r2 != "10.10.10.10" {
                        sleep 10000
                    }
                    if r2 == 3 {
                        sleep 10000
                    }
                    if r2 == r1 {
                        sleep 10000
                    }
                    resolve "bad"
                    store r2
                    assert r2 == ""
                }
                load r1
                store r2
            }
        """
        run_program(source=text, target='127.0.0.1:1053')

    @app.command()
    def run(program: str='sploit.txt', target='127.0.0.1:1053', quiet: bool=False):
        if quiet:
            logger.setLevel(logging.getLevelName('WARNING'))
        with open(program) as fobj: text = fobj.read()
        run_program(source=text, target=target)

    app()

if __name__ == '__main__':
    cli()
