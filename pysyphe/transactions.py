# -*- coding: utf-8 -*-

import traceback
from contextlib import contextmanager

from .exceptions import TransactionException, WeAreDoomedException


class TransactionHandler(object):
    """ Two phase commit handler.

    TransactionHandler is the interface used by the TransactionsManager to manage a transaction.

    The method `begin` will be called at the begginning for all the managed transactions.
    You should acquire locks in the beginning phase.

    Then `execute` will be called. Data modifications should be done there.
    If the method raises any exception, the transaction is failed.

    If any transaction fails, `rollback` will be called on all the managed transactions.
    `rollback` should undo everything done in execute and release locks if any.

    If all executions succeed, `prepare_commit` will be called. It returns True if the transaction is ready
    to be commited. When all transactions commit are prepared, `commit` will be called by the transactions
    manager. If any transaction handler's commit preparation fails, all transactions will be rollbacked.

    Reliability of the transaction depends on the confidence we can have in the prepare_commit->commit phase.
    If the probability of a fail of the commit phase after a successfull commit preparation is high,
    then the transaction is not reliable.

    There is cases when commit can't be prepared (with simple mysql transaction for example) and then commit
    may fail. The manager will do this kind of commit first.

    The transactions manager calls `can_prepare_commit` on all the transaction handlers to know if a commit
    can be prepared.

    Warning:
        The rollback may be called before the execute or even the begin. It is up to your transaction handler
        to be ready for that.
        The rollback may be called after the commit if another transaction commit fails. If the transaction
        has a way to rollback commmited things, it shoulds do it.
    """

    def begin(self):
        pass

    def execute(self):
        pass

    def rollback(self):
        pass

    def can_prepare_commit(self):
        return False

    def prepare_commit(self):
        pass

    def commit(self):
        pass


class TransactionsManager(object):
    """ Coordinate several transaction handlers with a two phase commit protocol.
    See TransactionHandler for a description of this protocol.

    You must add transaction handlers to the transactions manager before begining the transactions.
    Then the transaction manager must be used as a context manager:
    ```
        trm = TransactionsManager()
        trm.add_transaction_handler(transaction_handler)
        with trm.begin():
            trm.execute()
            trm.commit()
    ```
    Any exception under the context manager will be handled by the transaction manager that will rollback
    everything.

    If you want to protect you transactions with a mutex, you should set a mutex handler. It is a transaction
    handler that will be called first and commited/rollbacked last to protect the whole process.

    Warning:
        The rollback may be called before the execute or even the begin. It is up to your transaction handler
        to be ready for that.
    """

    def __init__(self):
        self._transaction_handlers = []
        self._mutex_handler = TransactionHandler()
        self._begun = False
        self._already_rollbacked = False
        self.exceptions_encountered = []

    def add_transaction_handler(self, transaction_handler):
        """ Add a transaction handler.
        Order is preserved, the first handler to be added will be the first to be called at each step.
        You can't add a handler after the call to `begin`.
        """
        if self._begun:
            raise TransactionException("Transactions have begun!")
        self._transaction_handlers.append(transaction_handler)

    def set_mutex_handler(self, mutex_handler):
        """ Set the mutex handler. Mutex handler is a transaction handler but it is always begun first and
        rollbacked/commited last.
        The transaction steps for the mutex handler are simpler: begin is called at the beginning before the
        other transactions and commit/rollback at the end after the others, the other steps are skipped.
        Args:
            mutex_handler (TransactionHandler)
        """
        if self._begun:
            raise TransactionException("Transactions have begun!")
        self._mutex_handler = mutex_handler

    def _add_exception_encoutered(self, exception):
        """ Add an exception and its traceback to the attribute exceptions_encountered.
        It will add only if last exception is not the same.
        """
        # Exception may have been already added to self.exceptions_encountered
        # if rollback has been already called for example.
        if (
            not self.exceptions_encountered
            or self.exceptions_encountered[-1][0] != exception
        ):
            self.exceptions_encountered.append((exception, traceback.format_exc()))

    @contextmanager
    def begin(self):
        """ Context manager to begin all transactions. Call `begin` on all transaction handlers. """
        # TODO: currently one can call execute, rollback, etc outside of the context manager because the begun
        # attribute is not reset at the end of this method.
        self._already_rollbacked = False
        self.exceptions_encountered = []
        try:
            self._begun = True
            # mutex handler first
            self._mutex_handler.begin()
            # classic transactions handler next in same order as appended.
            for transaction_handler in self._transaction_handlers:
                transaction_handler.begin()
            yield
        except Exception as e:
            self._add_exception_encoutered(e)
            if self._already_rollbacked:
                # "raise WeAreDoomedException from" en python3
                traceback_encountered = [
                    traceback_txt for _exc, traceback_txt in self.exceptions_encountered
                ]
                raise WeAreDoomedException(
                    "Transactions already rollbacked", traceback_encountered
                )
            else:
                try:
                    self.rollback()
                except Exception as rlb_e:
                    self._add_exception_encoutered(rlb_e)
                    traceback_encountered = [
                        traceback_txt
                        for _exc, traceback_txt in self.exceptions_encountered
                    ]
                    raise WeAreDoomedException(
                        "Transactions rollbacking failed.", traceback_encountered
                    )
            raise

    def execute(self):
        """ Call `execute` on all transaction handlers.
        Can't call execute if transactions have not begun.
        """
        if not self._begun:
            raise TransactionException("Transactions have not begun!")
        for transaction_handler in self._transaction_handlers:
            transaction_handler.execute()

    def rollback(self):
        """ Call `rollback` on all transaction handlers.
        Can't call rollback if transactions have not begun.
        All exceptions encountered during rollbacks will be saved in self.exceptions_encountered and last exception
        will be re-raised. So, all rollbacks are called even if one fails.
        """
        if not self._begun:
            raise TransactionException("Transactions have not begun!")
        self._already_rollbacked = True
        last_exc = None
        # Classic transactions first in the same order as appended.
        for transaction_handler in self._transaction_handlers:
            try:
                transaction_handler.rollback()
            except Exception as e:
                self.exceptions_encountered.append((e, traceback.format_exc()))
                last_exc = e
        # mutex handler last.
        try:
            self._mutex_handler.rollback()
        except Exception as e:
            self.exceptions_encountered.append((e, traceback.format_exc()))
            last_exc = e
        if last_exc:
            raise last_exc

    def commit(self):
        """ Call `commit` on all transaction handlers.
        Can't call commit if transactions have not begun.
        Commit has two steps: for each handler that can prepare commit, `prepare_commit` will be called. If any commit
        preparation fails, rollback is called. When all transaction's commits are prepared, commit is called begining with
        transactions whose commit can't be prepared.
        """
        if not self._begun:
            raise TransactionException("Transactions have not begun!")
        # Two phase commit.
        # Prepare commit for all transactions.
        prepare_commit_trs = [
            transaction_handler
            for transaction_handler in self._transaction_handlers
            if transaction_handler.can_prepare_commit()
        ]
        if any(
            not transaction_handler.prepare_commit()
            for transaction_handler in prepare_commit_trs
        ):
            # Prepare commit has failed. We rollback.
            self.rollback()
            return
        # All commit have been prepared.
        # We commit first those who can't be prepared.
        no_prepare_commit_trs = [
            transaction_handler
            for transaction_handler in self._transaction_handlers
            if not transaction_handler.can_prepare_commit()
        ]
        for transaction_handler in no_prepare_commit_trs:
            transaction_handler.commit()
        for transaction_handler in prepare_commit_trs:
            transaction_handler.commit()
        self._mutex_handler.commit()
        # FYI: since commit should be done inside the begin context managing, if a commit fails, even the last, rollback will be
        # done. We could have decided to throw an exception if a prepare_commit fails for the same begin context manager to
        # rollback for us. TODO: we could even decide that prepare_commit shouldn't return a boolean but only throw an exception
        # if it has failed. It would be better !


class PipelineTransactionHandler(TransactionHandler):
    """ A pipeline transaction is a transaction that execute an ActionPipeline.
        There is no commit possible in this transaction. If we must rollback, the pipeline is done backward to undo things.
    """

    def __init__(self, actions_pipeline=None):
        """ Contruct the handler
        Args:
            actions_pipeline: the pipeline of action to be executed. Should inherit from actions.Action.
        """
        self._actions_pipeline = None
        if actions_pipeline:
            self.actions_pipeline = actions_pipeline  # Will call property setter.

    @property
    def actions_pipeline(self):
        """ Get the pipeline to be executed. You should only read things from the pipeline """
        return self._actions_pipeline

    @actions_pipeline.setter
    def actions_pipeline(self, actions_pipeline):
        """ Set the pipeline to be executed. actions_pipeline should inherit from actions.Action."""
        self._actions_pipeline = actions_pipeline
        # To reduce stack trace deepness.
        self.execute = self.actions_pipeline.do
        self.rollback = self.actions_pipeline.undo

    @property
    def pipeline_name(self):
        """ Get the pipeline name """
        return self._actions_pipeline.name

    @pipeline_name.setter
    def pipeline_name(self, value):
        """ The pipeline name is read only """
        raise TransactionException(
            "Pipeline name is read only. "
            "You should change the name of the pipeline directly on the pipeline object."
        )

    def execute(self):
        # execute is redefined in actions_pipeline.setter
        raise TransactionException("No actions pipeline defined.")

    def rollback(self):
        # rollback is redefined in actions_pipeline.setter
        raise TransactionException("No actions pipeline defined.")

    def can_prepare_commit(self):
        # Since a pipeline transaction does not do commit, the prepare-commit->commit phase is reliable
        # and we can assure transaction manager that the commit will not fail.
        # In fact, the pipeline could have a method to checks that everything is correct in the prepare commit phase.
        return True

    def prepare_commit(self):
        return True
