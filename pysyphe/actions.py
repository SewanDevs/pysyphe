# -*- coding: utf-8 -*-

import sys
import inspect
from copy import copy
from functools import partial
from contextlib import contextmanager

from .data_structs import ReferencesDict, ReversibleList
from .streamers import InfoStreamer
from .exceptions import ActionException

if sys.version_info < (3, 0):
    from .py2 import InstanceMethod, StaticMethod
try:
    from contextlib import nested
except ImportError:
    from .py3 import nested

# TODO: add a propery to have the name of an action, for pipeline action too.


class Action(object):
    """ An action is an object that knows how to rollback.
        Call do to do the action.
        Call undo to rollback the action.

        You can add callbacks with context managers ! You have access to the action object inside the context manager.
        @contextmanager
        def log_things(action):
            logging.info("I am before the action")
            yield  # Action will be done here
            logging.info("I am after the action")

        It may be used to catch exception raised by the action and do things with it.
        If you call action.do() inside the except clause, you can retry things:
        @contextmanager
        def retry_action_3_times_if_its_a_connection_problem(action):
            try:
                yield
            except RequestTimeout:
                action.retries = getattr(action, "retries", 0) + 1
                if action.retries < 3:
                    action.do()

        But if you catch the exception and don't reraise it, the action may be considered successful.

        To get info on what will be done, set a streamer objet with set_info_streamer.
        A streamer is an objet that exposes one method: send_info. See streamers.py.
    """

    def __init__(self, action_fct=None, rollback_fct=None):
        """ Attributes:
                action_fct (function) The function that will be called in do(). It shoulds take no param.
                rollback_fct (function) The function that will be called in undo(). It shoulds take no param.
        """
        self._context_managers = {"action": [], "rollback": []}
        self._names = {"action": [], "rollback": []}
        self.info_streamer = InfoStreamer()  # InfoStreamer does nothing actually.
        self._action_fct = action_fct
        self._rollback_fct = rollback_fct

    @property
    def name(self):
        return self.get_name("action")

    @name.setter
    def name(self, value):
        self.set_name("action", value)

    @property
    def rollback_name(self):
        return self.get_name("rollback")

    @rollback_name.setter
    def rollback_name(self, value):
        self.set_name("rollback", value)

    def get_name(self, action_side):
        if action_side not in self._names.keys():
            raise ActionException("Wrong action type ({}). Available: {}"
                                  .format(action_side, ", ".join(self._names.keys())))
        return self._names[action_side]

    def set_name(self, action_side, value):
        if action_side not in self._names.keys():
            raise ActionException("Wrong action type ({}). Available: {}"
                                  .format(action_side, ", ".join(self._names.keys())))
        self._names[action_side] = value

    def do(self):
        if not self._action_fct:
            raise ActionException("Can't do: no action function defined.")
        ctx_managers = [ctx_manager_gen(self) for ctx_manager_gen in reversed(self._context_managers["action"])]
        # In python 3 use contextlib.ExitStack
        with nested(*ctx_managers):
            return self._action_fct()

    def undo(self):
        if not self._rollback_fct:
            raise ActionException("Can't undo: no rollback function defined.")
        ctx_managers = [ctx_manager_gen(self) for ctx_manager_gen in reversed(self._context_managers["rollback"])]
        # In python 3 use contextlib.ExitStack
        with nested(*ctx_managers):
            return self._rollback_fct()

    def add_context_manager(self, action_side, context_manager, inner=False):
        """ Context managers are nested, so the last context manager added will be the first entered
            and the last exited, i.e. the outermost one.
            Set inner to True, if you want the context manager to be the innermost one.

            context_manager must be a callable (has __call__) that takes an action and returns a context manager.
            Use the @contextmanager to do that easily.
        """
        if action_side not in self._context_managers.keys():
            raise ActionException("Wrong action type ({}). Available: {}"
                                  .format(action_side, ", ".join(self._context_managers.keys())))
        if inner:
            self._context_managers[action_side].insert(0, context_manager)
        else:
            self._context_managers[action_side].append(context_manager)

    def action_context_manager(self, context_manager):
        self.add_context_manager("action", context_manager)
        # Returning the context_manager for the original context_manager to be still usable as a context_manager
        # if this method is used as a decorator
        return context_manager

    def rollback_context_manager(self, context_manager):
        self.add_context_manager("rollback", context_manager)
        # Returning the context_manager for the original context_manager to be still usable as a context_manager
        # if this method is used as a decorator
        return context_manager

    def set_info_streamer(self, info_streamer):
        self.info_streamer = info_streamer
        if not hasattr(self.info_streamer, "send_info"):
            raise ActionException("Info streamer must have a method send_info.")

    def __copy__(self):
        newone = type(self)()
        newone.__dict__.update(self.__dict__)
        # The only problem comes from _context_managers, so we will recreate a dict with lists
        newone._context_managers = {
            "action": [cm for cm in self._context_managers["action"]],
            "rollback": [cm for cm in self._context_managers["rollback"]]}
        return newone

    def simulate(self, *args, **kwargs):
        """ Will simulate the action type but without calling it.
            The _action_fct/_rollback_fct will not be called. Context managers will not be executed.
            But the internal state, if any, will be changed as if the action was done """
        # no internal state
        pass

    def _get_action_name(self, action_side):
        # TODO: Generate action names when defining _action and rollback_action to give
        # possibility to change action name afterwards. See global TODO about action name.
        # TODO: currently, for _rollback_fct, the class name is missing....
        # TODO: everything here is a bit messy. _class added by AddClassToCallable is necessary but this
        # code needs to know the existence of this AddClassToCallable, it is not very clean...
        if action_side == "action":
            fct = self._action_fct
        else:
            fct = self._rollback_fct
        if isinstance(fct, partial):
            fct = fct.func
        if not inspect.isfunction(fct):
            return str(fct)

        if sys.version_info >= (3, 0):
            name = fct.__qualname__.replace('<locals>.', '')
        else:
            if hasattr(self, "_class") and action_side == "action":
                fct._class = self._class  # _class added by AddClassToCallable
            if hasattr(fct, "_class"):
                # Thanks to ActionsClass metaclass
                name = '{}.{}'.format(fct._class.__name__, fct.__name__)
            else:
                name = fct.__name__
        if fct.__globals__["__name__"] != "__main__":
            name = '{}.{}'.format(fct.__globals__["__name__"], name)
        return name


class StatefullAction(Action):
    """ StatefullAction will handle actions that keep a state.
        The state is set at the preparation of the action. It fixes the parameters of the action. The action may modify
        this state to know what have been done and to keep value for the rollback or for other actions.

        It may be used as a decorator to define the action. Use statefull_action decorator directly.

        You must define the items of the state that are mandatory for your action or your rollback.
        And you may save values in the state for other action to read it.

        A statefullAction may have a rollback but its not mandatory.
        A statefullAction may be done partially. So it may have to do partial rollback. It means that it's up to the rollback
        function to know what must be undone and the rollback function will be called even if the action has failed (even if the
        action has not been called because of an exception in a context manager.)

        @statefull_action(state_items=["text"])
        def my_action(state):
            text = state["text"]
            state["before_text"] = text[::-1]
            print(text)

        @my_action.rollback_action(state_items=["before_text"])
        def my_action_rollback(state):
            text = state["before_text"]
            print(text)

        @my_action.action_context_manager
        @contextmanager
        def say_something_before_my_action(action):
            print("YOLO ?")
            yield
            print("Nope !")

        A StatefullAction must be prepared to be usable. The preparation will set the parameters of the action, will freeze
        it to be unmodifable and will construct the internal state.
        The preparation of an action returns a copy of the action. The original object may be prepared many times.

        # Now that I have an action, I need to prepare it with params:
        prepared_action = my_action.get_prepared_action(text="I don't know what I'm doing. I hope someone will clean up my mess!")

        prepared_action.do()
        # YOLO ?
        # I don't know what I'm doing. I hope someone will clean up my mess!
        # Nope !
        prepared_action.undo()
        # !ssem ym pu naelc lliw enoemos epoh I .gniod m'I tahw wonk t'nod I

        # The original decorated function is still usable as a function:
        my_action({"text": Still works!"})
        # Still works!
        # The original rollback action is still usable as a function
        my_action_rollback({"before_text": Still works!"})
        # Still works!
        # The original contextmanager is still usable as a contextmanager
        with say_something_before_my_action(None):
            print("Yes")
        # YOLO ?
        # yes
        # Nope !

        A prepared action may use reference to other actions' states to use these other actions' state as a parameters.
        prepared_action = my_action.get_prepared_action(text="ABC")
        prepared_action_2 = my_action.get_prepared_action(text=prepared_action.state.ref_to("before_text"))
        prepared_action.do()
        # ABC
        prepared_action_2.do()
        # CBA
        prepared_action.undo()
        # CBA
        prepared_action_2.undo()
        # ABC
    """

    def __init__(self, action_state_items=None, action_fct=None):
        self._action_state_items = action_state_items or []
        self._rollback_state_items = []
        # State will be initialized during the action preparation.
        # So, we know that action is prepared if _state is not None.
        self._state = None
        if action_fct:
            self._check_fct(action_fct)
        super(StatefullAction, self).__init__(action_fct=action_fct)

    @property
    def state(self):
        if not self._state:
            raise ActionException('You must prepare the action with get_prepared_action before accessing to the state')
        return self._state

    @state.setter
    def state(self, value):
        raise ActionException("State is read only")

    def action(self, fct):
        if self._action_fct:
            raise ActionException("Action already defined.")
        self._check_fct(fct)
        self._action_fct = fct
        # Returning self, because the fct and the action will be the same thing
        return self

    def __call__(self, state):
        if self._state is not None:
            raise ActionException("Can't use action like a function if action has been prepared.")
        if not self._action_fct:
            raise ActionException('Action is not defined')
        return self._action_fct(state)

    def rollback_action(self, state_items=None, fct=None):
        self._rollback_state_items = state_items or []

        def decorator(decorated_fct):
            if self._rollback_fct:
                raise ActionException("Rollback action already defined.")
            self._check_fct(decorated_fct)
            self._rollback_fct = decorated_fct
            # Returning the function for the original decorated rollback function to be still usable as a function.
            # But it is a problem for the AddClassToCallable thing because of python2 instancemethod that can't have custom attrs.
            # Sorry for that:
            if sys.version_info > (3, 0):
                return decorated_fct
            else:
                return InstanceMethod(decorated_fct)
        # We can use rollback_action like a decorator a directly like a classic method.
        if fct:
            return decorator(fct)
        else:
            return decorator

    def get_prepared_action(self, **kwargs):
        if not self._action_fct:
            raise ActionException('Action is not defined')
        if self._state is not None:
            raise ActionException("Action already prepared.")
        # Checks that all needed items are in kwargs.
        self._check_kwargs_for_action(kwargs)
        # Make a copy of the action before creating and freezing things.
        prepared_action = copy(self)
        # Prepare state
        prepared_action._state = ReferencesDict(kwargs)
        # Prepare action
        # Using partial because it preserves the name of the function and does not add up to the stacktrace.
        prepared_action._action_fct = partial(prepared_action._action_fct, prepared_action._state)
        # We can't check that all items needed for rollback action are set until action has been done.
        # So we will check that in a context manager around the _action.
        # We will use context manager for logging and items checking because it gives the possibility
        # of doing things before and after the self._action and to handle exceptions without increasing the size of the callstack.
        # This context manager will be the innermost one to be sure that other context manager does not do magic with the state.
        prepared_action.add_context_manager("action", type(self)._checks_store_items_for_rollback, inner=True)
        # Logging should be done at the really beginning and at the really end because other context manager could fail.
        # So we set logging to be the outermost context manager. It must be at the end of the context manager list.
        prepared_action.add_context_manager("action", type(self)._logging_do)
        # Prepare rollback
        if prepared_action._rollback_fct:
            prepared_action._rollback_fct = partial(prepared_action._rollback_fct, prepared_action._state)
            prepared_action.add_context_manager("rollback", type(self)._logging_undo)
        else:
            # If no rollback is set, we will set a fake one for undo method to work.
            # And we will not set any logging for this rollback.
            prepared_action._rollback_fct = lambda: None
        return prepared_action

    @staticmethod
    def _check_fct(fct):
        # Only function or staticmethod are authorized. Instance method would have no usefullness
        # because all params must come from the state.
        if not hasattr(fct, "__call__"):
            raise ActionException("{} is not a callable".format(fct))
        if len(inspect.getargspec(fct).args) != 1:
            raise ActionException("Callable must take one argument: the state.")

    def _check_kwargs_for_action(self, kwargs):
        missing_args = set(self._action_state_items) - set(kwargs.keys())
        if missing_args:
            raise ActionException("Missing args for the action preparation: {}".format(", ".join(missing_args)))
        # Checks that all items used in the action are defined in the decorator.
        superfluous_args = set(kwargs.keys()) - set(self._action_state_items)
        if superfluous_args:
            raise ActionException("Superfluous args for the action preparation: {}".format(", ".join(superfluous_args)))

    @contextmanager
    def _checks_store_items_for_rollback(self):
        try:
            yield
            # We will only check missing args because items in state after action are not only for rollback
            # but potentially for other actions.
            missing_items = set(self._rollback_state_items) - set(self._state.keys())
            if missing_items:
                raise ActionException("Missing items in state for the rollback action: {}".format(", ".join(missing_items)))
        except Exception:
            # We will check missing args only if action was successfull. If it was not, we will add an item "action_failed"
            # to help rollback knows that state is missing lots of thing.
            # It will be up to the rollback developer to remove this state if he wants the action to be re-done after rollback.
            self._state["action_failed"] = True
            raise  # re-raise exception

    @contextmanager
    def _logging_do(self):
        action_name = self._get_action_name("action")
        self.info_streamer.send_info(action_name=action_name, state=self._state, begin=True)
        try:
            yield
            self.info_streamer.send_info(action_name=action_name, state=self._state, end=True)
        except Exception as e:
            # TODO: remove some levels of exception traceback to see exception from the point of view of the action function
            self.info_streamer.send_info(action_name=action_name, state=self._state, end=True, exc=e)
            raise e

    @contextmanager
    def _logging_undo(self):
        rollback_action_name = self._get_action_name("rollback_action")
        action_name = self._get_action_name("action")
        self.info_streamer.send_info(action_name=rollback_action_name, state=self._state,
                                     rollback_of=action_name, begin=True)
        try:
            yield
            self.info_streamer.send_info(action_name=rollback_action_name, state=self._state, end=True)
        except Exception as e:
            # TODO: remove some levels of exception traceback to see exception from the point of view of the rollback function
            self.info_streamer.send_info(action_name=rollback_action_name, state=self._state, end=True, exc=e)
            raise e

    def simulate(self, action_side, after_state):
        # if this state have references to others states, since these other states have already been simulated, the value
        # can't change anymore and the correct values are in after_state.
        # But if other states have reference to this state we should keep the binding, so we have to keep the same object and
        # not recreate a new ReferencesDict.
        # Warning. /!\ The state after the rollback may be different from the state before the action...
        # Re-doing action with the the after-rollback-state may be dangerous.
        self._state.update(after_state or {})
        self.info_streamer.send_info(action_name=self._get_action_name(action_side), state=self._state, simul=True)


def statefull_action(state_items):
    def StatefullActionConstructor(fct):
        return StatefullAction(action_state_items=state_items, action_fct=fct)
    return StatefullActionConstructor


class UnitAction(StatefullAction):
    """ UnitAction will handle the unit actions: action that are statefull and can't be divided into smaller actions.
        The action can't be done partially so the rollback is called only if the action was successfull.
        Use unit_action decorator to create one.
    """

    def __init__(self, action_state_items=None, action_fct=None):
        super(UnitAction, self).__init__(action_state_items, action_fct)
        # To handle the atomicity of the action, we will prevent a prepared action to rollback
        # unless it has first successfully done the action. To do so, we will hide undo method using this attribute.
        self._undo_hidden = None

    @contextmanager
    def _enables_rollback(self):
        yield
        self.undo = self._undo_hidden

    def get_prepared_action(self, **kwargs):
        if not self._rollback_fct:
            raise ActionException('Rollback action is not defined for {}'.format(self._get_action_name("action")))
        prepared_action = super(UnitAction, self).get_prepared_action(**kwargs)
        # As commented in __init__, we will hide the undo method until action has been done:
        prepared_action._undo_hidden = prepared_action.undo
        prepared_action.undo = lambda: None  # A lambda to be still callable
        # rollback reactivation will be the innermost context manager to enables it as soon as action has been done.
        prepared_action.add_context_manager("action", type(self)._enables_rollback, inner=True)
        return prepared_action

    def simulate(self, action_side, after_state):
        if action_side == "action":
            with self._enables_rollback():
                pass
        super(UnitAction, self).simulate(action_side, after_state)


def unit_action(state_items):
    def UnitActionConstructor(fct):
        return UnitAction(action_state_items=state_items, action_fct=fct)
    return UnitActionConstructor


class ActionsPipeline(Action):
    """ ActionPipeline is an action that execute a pipeline of action with do and the rollback of every action done with undo.
        And you can add callbacks like other actions.
    """

    def __init__(self):
        # Here, _action_fct and _rollback_fct are defined as methods in the class.
        # But Action constructor sets _action_fct and _rollback_fct, so we need to give the methods to the constructor.
        # TODO: It may be a good idea that the fact the action is defined is handled without the fact that it equals to None.
        # It will permit to make _action_fct and _rollback_fct methods in the Action class directly !
        super(ActionsPipeline, self).__init__(action_fct=self._action_fct, rollback_fct=self._rollback_fct)
        self._actions_pipeline = ReversibleList()
        # Keep a pointer to all actions if we need to access them without moving forward in the pipeline.
        self._actions_list = list()

    @property
    def actions(self):
        return list(self._actions_list)  # return a copy

    @actions.setter
    def actions(self, value):
        raise ActionException("ActionsPipeline.actions is read-only")

    def append(self, action):
        # TODO or not TODO:
        # 1. Currently, if prepared action are linked together but not appended in the correct order,
        # it will not work correctly... We should add some checks that the other actions does not depend
        # on the currently appended action. But it would need something to see the links between states.
        # Not really usefull because it only prevent development error.
        # 2. Nothing checks that action is prepared and a not-prepared statefull action can't work.
        # But action preparation can't be determined externally.
        # Maybe we should have a StatefullActionFactory that creates action, it would be better.
        # TODO: why not a is_prepared attribute ? No, because action preparation is an internal concept of satefullaction...
        # Finally: StatefullActionFactory is maybe the more correct solution. But it address a problem that does not really exist,
        # A developer error that will be automatically detected at runtime. The only usefull thing would be to have something that
        # tells to the dev that the action is not prepared and not just something like "action takes 1 arg" in the do method.
        if not hasattr(action, "do") or not hasattr(action, "undo") or not hasattr(action, "set_info_streamer"):
            raise ActionException("action should inherit from Action.")
        self._actions_pipeline.append(action)
        self._actions_list.append(action)
        # Propagate info_streamer to sub actions
        action.set_info_streamer(self.info_streamer)

    def set_info_streamer(self, info_streamer):
        super(ActionsPipeline, self).set_info_streamer(info_streamer)
        # We wan't all actions in the pipeline to share the same info_streamer
        for action in self._actions_list:
            action.set_info_streamer(info_streamer)

    def _action_fct(self):
        for action in self._actions_pipeline:
            action.do()

    def _rollback_fct(self):
        self._actions_pipeline.reverse()
        try:
            for action in self._actions_pipeline:
                action.undo()
        finally:
            # Re-reverse to be able to redo actions if needed.
            self._actions_pipeline.reverse()

    def simulate_until(self, actions_already_done):
        """ Move pipeline forward without doing actions.
            actions_already_done is a list of (action_name, after_state) for the pipeline to be able
            to rollback correctly.
            If actions_already_done is longer than the pipeline length, the remaining actions are considered rollbacks action.
        """
        nb_action_simulated = 0
        for action_already_done, action in zip(actions_already_done, self._actions_pipeline):
            # Checks that action_name is correct.
            done_action_name = action_already_done[0]
            # We may consider action as a friend class of actionPipeline or choose a better way to access the action name:
            # TODO: add the name property !
            action_name = action._get_action_name("action")
            if done_action_name != action_name:
                # If the pipeline was partially done and then rollbacked, the actions_already_done may be some of the
                # actions and then a part of the corresponding rollbacks. Next action already done may be a rollback action name
                # we can't know here if the next done_action_name is the next rollback name or is an error.
                # So we will consider that it is not an error and we have gone too far in the actions list and it keeps
                # an internal state. We need to go back one action.
                self._actions_pipeline.reverse()
                next(self._actions_pipeline)
                self._actions_pipeline.reverse()
                break
            after_state = action_already_done[1]
            action.simulate("action", after_state=after_state)
            nb_action_simulated += 1
            # Action is now ready for rollback.

        if nb_action_simulated < len(actions_already_done):
            nb_rollback_simulated = 0
            # Some rollbacks action have already been done.
            self._actions_pipeline.reverse()
            for action_already_done, action in zip(actions_already_done[nb_action_simulated:], self._actions_pipeline):
                done_action_name = action_already_done[0]
                action_name = action._get_action_name("rollback")
                if done_action_name != action_name:
                    raise ActionException("Next action already done does not match next action in this pipeline: {} != {}"
                                          .format(done_action_name, action_name))
                after_state = action_already_done[1]
                action.simulate("rollback", after_state=after_state)
                nb_rollback_simulated += 1

            # List will be in the state corresponding to the actions already done.
            # To retry or rollback, one just needs to call do or undo on pipeline.
            self._actions_pipeline.reverse()

            if nb_action_simulated + nb_rollback_simulated < len(actions_already_done):
                # Not all actions were simulated...
                next_not_simulated = actions_already_done[nb_action_simulated + nb_rollback_simulated]
                # TODO: with nb_action_simulated and nb_rollback_simulated, we can determine the kind of error the
                # developer has done.
                raise ActionException("Not all action done were simulated. Can't simulate: {}".format(next_not_simulated[0]))

    def __copy__(self):
        other = super(ActionsPipeline, self).__copy__()
        # Action and rollback fct are special, they are in the __dict__ attributes because they are attributes in
        # the class Action. But here they are bound methods. We have to recreate it from class, because they are currently bound to self and not
        # to other, and rebind it.
        other._action_fct = ActionsPipeline._action_fct.__get__(other, ActionsPipeline)
        other._rollback_fct = ActionsPipeline._rollback_fct.__get__(other, ActionsPipeline)
        other._actions_pipeline = copy(self._actions_pipeline)
        other._actions_list = list(self._actions_list)
        return other


class AddClassToCallable(type):
    """ Metaclass to add a _class attr to all class's callable.
        Usefull to retrieve the class of a method inside an object created with a decorator since the decorator is called
        before class is build.
    """
    def __init__(cls, name, bases, attrs):
        for attr_name in attrs.keys():
            # For descriptor like staticmethod to get the original function:
            attr = getattr(cls, attr_name)
            if hasattr(attr, "__call__"):
                # Add a try except AttributeError, to handle AttributeError: 'instancemethod' object has no attribute '_class'
                # because class of this metaclass may defines others things than action and their rollback...
                attr._class = cls
        super(AddClassToCallable, cls).__init__(name, bases, attrs)


class Actions(object):
    __metaclass__ = AddClassToCallable


def staticaction(action):
    """ Use it instead of staticmethod to define actions inside classes. """
    # If action are defined inside class, the rollback_action decorator is used directly inside the class definition.
    # And if an action has been defined to be static (it should allways be the case), the rollback_action decorator is not
    # available directly (the descriptor mecanism of staticmethod can only apply after the construction of the class is finished).
    # We need to copy the decorator on the staticmethod object that encapsulates the real method.
    # TODO: maybe re-read how @properties are defined to see if there no better way.
    # TODO: to simplify usage and because all actions inside class should be static, we can transform every unit_action in subclasses
    # of Actions into staticmethod directly in the metaclass of Actions.
    if sys.version_info > (3, 3):
        staticaction_ = staticmethod(action)
    else:
        staticaction_ = StaticMethod(action)
    if isinstance(action, StatefullAction):
        staticaction_.rollback_action = action.rollback_action
    return staticaction_
