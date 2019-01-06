from types import GeneratorType
from functools import partial
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import Test, TestFail
from pythonwhat.Feedback import Feedback, InstructorError
import copy
import ast

def multi(*args, state=None):
    """Run multiple subtests. Return original state (for chaining).

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        tests: sub-SCTs that all should pass.

    :Example:

        Suppose we want to verify the following function call: ::

            round(1.2345, ndigits=2)

        The following SCT would verify this, using ``multi`` to
        'branch out' the state to two sub-SCTs: ::

            Ex().check_function('round').multi(
                check_args(0).has_equal_value(),
                check_args('ndigits').has_equal_value()
            )

    """
    if any(args):
        rep = Reporter.active_reporter

        # when input is a single list of subtests
        if len(args) == 1 and isinstance(args[0], (list, tuple, GeneratorType)):
            args = args[0]

        for test in args:
            # assume test is function needing a state argument
            # partial state so reporter can test
            rep.do_test(partial(test, state=state))

    # return original state, so can be chained
    return state

def check_not(*tests, msg, state=None):
    """Run multiple subtests that should fail. If all subtests fail, returns original state (for chaining)

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        tests: one or more sub-SCTs that all should not pass.
        msg: feedback if not all tests fail.

    :Example:
        The SCT fails with feedback for a specific incorrect value, defined using an override: ::

            Ex().check_object('result').multi(
                check_not(
                    has_equal_value(override=100),
                    msg='100 is incorrect for reason xyz.'
                ),
                has_equal_value()
            )

        Notice that ``check_not`` comes before the ``has_equal_value`` test
        that checks if the student value is equal to the solution value.

    :Example:
        The SCT below runs two ``has_code`` cases: ::

            Ex().check_not(
                has_code('mean'),
                has_code('median'),
                msg='Check your code'
            )

        If students use ``mean`` or ``median`` anywhere in their code, this SCT will fail.

    Note:
        - This function is not yet tested with all checks, please report unexpected behaviour.
        - This function can be thought as a NOT(x OR y OR ...) statement, since all tests it runs must fail
        - This function can be considered a direct counterpart of multi.

    """
    rep = Reporter.active_reporter

    for test in tests:
        try:
            multi(test, state=state)
        except TestFail:
            # it fails, as expected, off to next one
            continue
        return rep.do_test(Test(msg))

    # return original state, so can be chained
    return state

def check_or(*tests, state=None):
    """Test whether at least one SCT passes.

    If all of the tests fail, the feedback of the first test will be presented to the student.

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        tests: one or more sub-SCTs to run.

    :Example:

        The SCT below tests that the student typed either 'mean' or 'median': ::

            Ex().check_or(
                has_code('mean'),
                has_code('median')
            )

        If the student didn't type either, the feedback message generated by ``has_code(mean)``,
        the first SCT, will be presented to the student.

    """

    rep = Reporter.active_reporter

    success = False
    first_feedback = None
    for test in tests:
        try:
            multi(test, state=state)
            success = True
        except TestFail as e:
            if not first_feedback: first_feedback = e.feedback
        if success:
            return
    
    rep.do_test(Test(first_feedback))

def check_correct(check, diagnose, state=None):
    """Allows feedback from a diagnostic SCT, only if a check SCT fails.

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        check: An sct chain that must succeed.
        diagnose: An sct chain to run if the check fails.

    :Example:

        The SCT below tests whether an object is correct. Only if the object is not correct, will
        the function calling checks be executed ::

            Ex().check_correct(
                check_object('x').has_equal_value(),
                check_function('round').check_args(0).has_equal_value()
            )

    """
    feedback = None
    try:
        multi(check, state=state)
    except TestFail as e:
        feedback = e.feedback

    try:
        multi(diagnose, state=state)
    except TestFail as e:
        if feedback is not None or state.force_diagnose:
            feedback = e.feedback

    if feedback is not None:
        rep = Reporter.active_reporter
        rep.do_test(Test(feedback))

# utility functions -----------------------------------------------------------

def fail(msg="", state=None):
    """Fail SCT
    
    This function takes a single argument, ``msg``, that is the feedback given to the student.
    Note that this would be a terrible idea for grading submissions, but may be useful while writing SCTs.
    For example, failing a test will highlight the code as if the previous test/check had failed.

    :Example:
    
        As a trivial SCT example, ::

            Ex().check_for_loop().check_body().fail()

        This can also be helpful for debugging SCTs, as it can be used to stop testing as a given point.



"""
    rep = Reporter.active_reporter
    _msg = state.build_message(msg)
    rep.do_test(Test(Feedback(_msg, state)))

def override(solution, state=None):
    """Override the solution code with something arbitrary.

    There might be cases in which you want to temporarily override the solution code
    so you can allow for alternative ways of solving an exercise.
    When you use ``override()`` in an SCT chain, the remainder of that SCT chain will
    run as if the solution code you specified is the only code that was in the solution.

    Check the glossary for an example (pandas plotting)

    Args:
        solution: solution code as a string that overrides the original solution code.
        state: State instance describing student and solution code. Can be omitted if used with Ex().
    """

    # the old ast may be a number of node types, but generally either a
    # (1) ast.Module, or for single expressions...
    # (2) whatever was grabbed using module.body[0]
    # (3) module.body[0].value, when module.body[0] is an Expr node
    old_ast = state.solution_tree
    new_ast = ast.parse(solution)
    if not isinstance(old_ast, ast.Module) and len(new_ast.body) == 1:
        expr = new_ast.body[0]
        candidates = [expr, expr.value] if isinstance(expr, ast.Expr) else [expr]
        for node in candidates:
            if isinstance(node, old_ast.__class__): 
                new_ast = node
                break

    kwargs  = state.messages[-1] if state.messages else {}
    child = state.to_child_state(
            solution_subtree = new_ast,
            student_subtree = state.student_tree,
            highlight = state.highlight,
            append_message = {'msg': "", 'kwargs': kwargs}
            )

    return child


def set_context(*args, state=None, **kwargs):
    """Update context values for student and solution environments.
    
    When ``has_equal_x()`` is used after this, the context values (in ``for`` loops and function definitions, for example)
    will have the values specified throught his function. It is the function equivalent of the ``context_vals`` argument of
    the ``has_equal_x()`` functions.

    - Note 1: excess args and unmatched kwargs will be unused in the student environment.
    - Note 2: When you try to set context values that don't match any target variables in the solution code,
      ``set_context()`` raises an exception that lists the ones available.
    - Note 3: positional arguments are more robust to the student using different names for context values.
    - Note 4: You have to specify arguments either by position, either by name. A combination is not possible.

    :Example:

        Solution code::

            total = 0
            for i in range(10):
                print(i ** 2)

        Student submission that will pass (different iterator, different calculation)::

            total = 0
            for j in range(10):
                print(j * j)

        SCT::

            # set_context is robust against different names of context values.
            Ex().check_for_loop().check_body().multi(
                set_context(1).has_equal_output(),
                set_context(2).has_equal_output(),
                set_context(3).has_equal_output()
            )

            # equivalent SCT, by setting context_vals in has_equal_output()
            Ex().check_for_loop().check_body().\\
                multi([s.has_equal_output(context_vals=[i]) for i in range(1, 4)])

    """

    stu_crnt = state.student_context.context
    sol_crnt = state.solution_context.context

    # for now, you can't specify both
    if len(args) > 0 and len(kwargs) > 0:
        raise InstructorError("In `set_context()`, specify arguments either by position, either by name.")

    # set args specified by pos -----------------------------------------------
    if args:
        # stop if too many pos args for solution
        if len(args) > len(sol_crnt): 
            raise InstructorError("Too many positional args. There are {} context vals, but tried to set {}"
                                  .format(len(sol_crnt), len(args)))
        # set pos args
        upd_sol = sol_crnt.update(dict(zip(sol_crnt.keys(), args)))
        upd_stu = stu_crnt.update(dict(zip(stu_crnt.keys(), args)))
    else:
        upd_sol = sol_crnt
        upd_stu = stu_crnt

    # set args specified by keyword -------------------------------------------
    if kwargs:
        # stop if keywords don't match with solution
        if set(kwargs) - set(upd_sol):
            raise InstructorError("`set_context()` failed: context val names are {}, but you tried to set {}."
                                  .format(upd_sol or "missing", sorted(list(kwargs.keys()))))
        out_sol = upd_sol.update(kwargs)
        # need to match keys in kwargs with corresponding keys in stu context
        # in case they used, e.g., different loop variable names
        match_keys = dict(zip(sol_crnt.keys(), stu_crnt.keys()))
        out_stu = upd_stu.update({match_keys[k]: v for k,v in kwargs.items() if k in match_keys})
    else:
        out_sol = upd_sol
        out_stu = upd_stu

    return state.to_child_state(student_context = out_stu,
                                solution_context = out_sol,
                                highlight = state.highlight)

def set_env(state = None, **kwargs):
    """Update/set environemnt variables for student and solution environments.

    When ``has_equal_x()`` is used after this, the variables specified through this function will
    be available in the student and solution process. Note that you will not see these variables
    in the student process of the state produced by this function: the values are saved on the state
    and are only added to the student and solution processes when ``has_equal_ast()`` is called.

    :Example:

        Student and Solution Code::

            a = 1
            if a > 4:
                print('pretty large')

        SCT::

            # check if condition works with different values of a
            Ex().check_if_else().check_test().multi(
                set_env(a = 3).has_equal_value(),
                set_env(a = 4).has_equal_value(),
                set_env(a = 5).has_equal_value()
            )

            # equivalent SCT, by setting extra_env in has_equal_value()
            Ex().check_if_else().check_test().\\
                multi([has_equal_value(extra_env={'a': i}) for i in range(3, 6)])
    """

    stu_crnt = state.student_env.context
    sol_crnt = state.solution_env.context

    stu_new = stu_crnt.update(kwargs)
    sol_new = sol_crnt.update(kwargs)

    return state.to_child_state(student_env = stu_new,
                                solution_env = sol_new,
                                highlight = state.highlight)

def disable_highlighting(state = None):
    """Disable highlighting in the remainder of the SCT chain.

    Include this function if you want to avoid that pythonwhat marks which part of the student submission is incorrect.

    :Examples:

        SCT that will mark the 'number' portion if it is incorrect::

            Ex().check_function('round').check_args(0).has_equal_ast()

        SCT chains that will not mark certain mistakes. The earlier you put the function, the more types of mistakes will no longer be highlighted::

            Ex().disable_highlighting().check_function('round').check_args(0).has_equal_ast()
            Ex().check_function('round').disable_highlighting().check_args(0).has_equal_ast()
            Ex().check_function('round').check_args(0).disable_highlighting().has_equal_ast()
    """
    return state.to_child_state(highlighting_disabled = True)
