Pysyphe
=======
|pipeline_status| |coverage|

Helps you create and manage your own rollbackable transactions.

Installation
------------

.. code-block:: console

    $ pip install --trusted-host devpi.priv.sewan.fr --index-url http://devpi.priv.sewan.fr/sophia/prod/ pysyphe

Or, if your pipenv is correctly configured:

.. code-block:: console

    $ pipenv install pysyphe


Tests
------

Tests should be run under python 2.7 and python 3.6 to tests everything

.. code-block:: console

    $ pip install tox
    $ tox -e py27,py36

Coverage reports will be the merge of the coverage for py27 and py36.


Features
--------


**Rollbackable Actions**

Create actions and chain them in a pipeline:

.. code-block:: python


    >>> from pysyphe.actions import ActionsPipeline, Action
    >>> def hello_world():
    ...     print("Hello world!")
    ...
    >>> def im_alive():
    ...     print("I'm Alive!!!")
    ...
    >>> action1 = Action(hello_world)
    >>> action1.do()
    Hello world!
    >>> action2 = Action(im_alive)
    >>> pipeline = ActionsPipeline([action1, action2])
    >>> pipeline.do()
    Hello world!
    I'm Alive!!!


Create rollback for your actions:

.. code-block:: python

    >>> def hello_world():
    ...     print("Hello world!")
    ...
    >>> def goodbye_world():
    ...     print("Goodbye world!")
    ...
    >>> action = Action(hello_world, goodbye_world)
    >>> action.do()
    Hello world!
    >>> action.undo()
    Goodbye world!


Rollback pipelines:

.. code-block:: python

    >>> def hello_world():
    ...     print("Hello world!")
    ...
    >>> def goodbye_world():
    ...     print("Goodbye world!")
    ...
    >>> def im_alive():
    ...     print("I'm Alive!!!")
    ...
    >>> def im_dead():
    ...     print("I'm Dead!!!")
    ...
    >>> pipeline = ActionsPipeline([
    ...     Action(im_alive, im_dead),
    ...     Action(hello_world, goodbye_world)])
    >>> pipeline.undo()  # Nothing to rollback
    >>> pipeline.do()
    I'm Alive!!!
    Hello world!
    >>> pipeline.undo()  # Will be done in reverse order.
    Goodbye world!
    I'm Dead!!!


Rollback only what have been done:

.. code-block:: python

    >>> def hello_world():
    ...     print("Hello world!")
    ...
    >>> def goodbye_world():
    ...     print("Goodbye world!")
    ...
    >>> def im_alive():
    ...     print("I'm Alive!!!")
    ...
    >>> def im_dead():
    ...     print("I'm Dead!!!")
    ...
    >>> def failure():
    ...     raise Exception("I broke your pipeline, what are you gonna do?")
    ...
    >>> pipeline = ActionsPipeline([
    ...     Action(hello_world, goodbye_world),
    ...     Action(failure, lambda: None),  # rollback will be an empty function
    ...     Action(im_alive, im_dead)])
    >>> try:
    ...     pipeline.do()
    ... except Exception:
    ...     pipeline.undo()
    ...
    Hello world!
    Goodbye world!


Define actions with a state:

.. code-block:: python

    >>> from pysyphe.actions import statefull_action
    >>> @statefull_action(["name"])
    ... def hello(state):
    ...     print("Hello {}".format(state["name"]))
    ...     state["name"] = "Dear " + state["name"]
    ...
    >>> @hello.rollback_action()
    ... def goodbye(state):
    ...     print("Goodbye {}".format(state["name"]))
    ...
    >>> action = hello.get_prepared_action(name="reader")  # It must be prepared for state to be inialised
    >>> action.do()
    Hello reader
    >>> action.undo()
    Goodbye Dear reader
    >>> action.do()
    Hello Dear reader
    >>> action.do()
    Hello Dear Dear reader


Chain actions with a state:

.. code-block:: python

    >>> @statefull_action(["name"])
    ... def hello(state):
    ...     print("Hello {}".format(state["name"]))
    ...     state["name"] = "Dear " + state["name"]
    ...
    >>> @hello.rollback_action()
    ... def goodbye(state):
    ...     print("Goodbye {}".format(state["name"]))
    ...
    >>> action = hello.get_prepared_action(name="reader")
    >>> action2 = hello.get_prepared_action(name=action.state.ref_to("name"))  # We can access the state of a previous action but read only !
    >>> action3 = hello.get_prepared_action(name=action2.state.ref_to("name"))
    >>> pipeline = ActionsPipeline([action, action2, action3)])
    >>> pipeline.do()
    Hello reader
    Hello Dear reader
    Hello Dear Dear reader
    >>> pipeline.undo()
    Goodbye Dear Dear Dear reader
    Goodbye Dear Dear reader
    Goodbye Dear reader
    >>> pipeline.do()
    Hello Dear reader
    Hello Dear Dear reader
    Hello Dear Dear Dear reader
    >>> pipeline.undo()
    Goodbye Dear Dear Dear Dear reader
    Goodbye Dear Dear Dear reader
    Goodbye Dear Dear reader


**Transactions**

Create transaction handlers and manage them:

.. code-block:: python

    >>> from pysyphe.transactions import TransactionHandler, TransactionsManager
    >>> class LoggingTransactionHandler(TransactionHandler):
    ...     def __init__(self, name, will_fail):
    ...         self.name = name
    ...         self.will_fail = will_fail
    ...     def begin(self):
    ...         print("BEGIN {}!".format(self.name))
    ...     def execute(self):
    ...         if self.will_fail:
    ...             raise Exception("Your transaction failed, what are you gonna do?")
    ...     def commit(self):
    ...         print("COMMIT {}!".format(self.name))
    ...     def rollback(self):
    ...         print("ROLLBACK {}!".format(self.name))
    ...
    >>> tran_success = LoggingTransactionHandler("first", will_fail=False)
    >>> tran_fail = LoggingTransactionHandler("second", will_fail=True)
    >>> manager = TransactionsManager()
    >>> manager.add_transaction_handler(tran_success)
    >>> with manager.begin():
    ...     manager.execute()
    ...     manager.commit()
    ...
    BEGIN first!
    COMMIT first!
    >>> manager = TransactionsManager()
    >>> manager.add_transaction_handler(tran_success)
    >>> manager.add_transaction_handler(tran_fail)
    >>> with manager.begin():  # The transaction manager will rollback all transactions if an exception occurs.
    ...     manager.execute()
    ...     manager.commit()
    ...
    BEGIN first!
    BEGIN second!
    ROLLBACK first!
    ROLLBACK second!
    Traceback (most recent call last):
      File "<stdin>", line -, in <module>
      File ".../pysyphe/transactions.py", line -, in execute
        transaction_handler.execute()
      File "<stdin>", line -, in execute
    Exception: Your transaction failed, what are you gonna do?


TODOs
------
- Generate the documentation
- Add a "How-To correctly write unit actions to get the most out of pysyphe" into the documentation

.. |pipeline_status| image:: https://gitlab.priv.sewan.fr/sophia/pysyphe/badges/master/pipeline.svg
   :target: https://gitlab.priv.sewan.fr/sophia/pysyphe/pipelines
.. |coverage| image:: https://gitlab.priv.sewan.fr/sophia/pysyphe/badges/master/coverage.svg
   :target: https://gitlab.priv.sewan.fr/sophia/pysyphe/commits/master
