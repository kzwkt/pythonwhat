import ast
from pythonwhat.State import State
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import Test
from pythonwhat.utils import get_ord
from pythonwhat.Feedback import Feedback
from pythonwhat.sub_test import sub_test

from functools import partial

def test_for_loop(index=1,
                  for_iter=None,
                  body=None,
                  orelse=None,
                  expand_message=True,
                  state=None):
    """Test parts of the for loop.

    This test function will allow you to extract parts of a specific for loop and perform a set of tests
    specifically on these parts. A for loop consists of two parts: the sequence, `for_iter`, which is the
    values over which are looped, and the `body`. A for loop can have a else part as well, `orelse`, but
    this is almost never used.

        | ``for i in range(10):``
        |     ``print(i)``

    Has `range(10)` as the sequence and `print(i)` as the body.

    Args:
      index (int): index of the function call to be checked. Defaults to 1.
      for_iter: this argument holds the part of code that will be ran to check the sequence of the for loop.
        It should be passed as a lambda expression or a function. The functions that are ran should
        be other pythonwhat test functions, and they will be tested specifically on only the sequence part of
        the for loop.
      body: this argument holds the part of code that will be ran to check the body of the for loop.
        It should be passed as a lambda expression or a function. The functions that are ran should
        be other pythonwhat test functions, and they will be tested specifically on only the body of
        the for loop.
      orelse: this argument holds the part of code that will be ran to check the else part of the for loop.
        It should be passed as a lambda expression or a function. The functions that are ran should
        be other pythonwhat test functions, and they will be tested specifically on only the else part of
        the for loop.
      expand_message (bool): if true, feedback messages will be expanded with `in the ___ of the for loop on
        line ___`. Defaults to True. If False, `test_for_loop()` will generate no extra feedback.

    Examples:
        Student code

        | ``for i in range(10):``
        |       ``print(i)``

        Solution code

        | ``for n in range(10):``
        |     ``print(n)``

        SCT

        | ``test_for_loop(1,``
        |     ``for_iter = lamdba: test_function("range"),``
        |     ``body = lambda: test_expression_output(context_val = [5])``

        This SCT will evaluate to True as the function `"range"` is used in the sequence and the function
        `test_exression_output()` will pass on the body code.
    """
    rep = Reporter.active_reporter
    rep.set_tag("fun", "test_for_loop")

    index = index - 1

    state.extract_for_calls()
    student_fors = state.student_for_calls
    solution_fors = state.solution_for_calls

    try:
        target_student, for_iter_student, body_student, orelse_student = student_fors[index]
    except:
        rep.do_test(Test("Define more `for` loops."))
        return

    target_solution, for_iter_solution, body_solution, orelse_solution = solution_fors[index]

    prepend_fmt = "Check your code in the {incorrect_part} of the %s for loop. " %(get_ord(index + 1))

    psub_test = partial(sub_test, state, rep, 
            expand_message=expand_message and prepend_fmt)

    psub_test(for_iter, for_iter_student, for_iter_solution, "sequence part")
    psub_test(body, body_student, body_solution, "body", target_student, target_solution)
    psub_test(orelse, orelse_student, orelse_solution, "else part", target_student, target_solution)