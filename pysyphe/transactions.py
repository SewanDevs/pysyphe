# -*- coding: utf-8 -*-

import traceback
from contextlib import contextmanager

from .exceptions import TransactionException, WeAreDoomedException


class TransactionHandler(object):
    """ Two phase commit handler.
        TransactionHandler is the interface used by the TransactionsManager to manage a transaction.

        The method "begin" will be called at the begginning for all the managed transactions.
        You should acquire lock in the begginning phase.

        Then "execute" will be called. Data modifications should be done there.
        If the method raises any exception, the transaction is failed.

        If any transaction fails, "rollback" will be called on all the managed transactions.
        "rollback" should undo everything done in execute and release locks if any.

        If all transaction succeeds, "prepare_commit" will be called. It returns True if the transaction is ready to be commited.
        When all transactions commit are prepared, "commit" will be called by the transactions manager.
        If any transaction handler commit preparation fails, all transactions will be rollbacked.

        Reliability of the transaction depends on the confidence we can have in the prepare_commit->commit phase.
        If the probability of a fail of the commit phase after a successfull commit preparation is high,
        then the transaction is not reliable.

        There is cases when commit can't be prepared (with simple mysql transaction for example) and then commit may fail.
        It will be more reliable if the manager do this kind of commit first.

        If transaction uses locks, they should be acquired in the begin phase and released in the rollback and commit phase.
    """

    def begin(self, *args, **kwargs):
        pass

    def execute(self, *args, **kwargs):
        pass

    def rollback(self, *args, **kwargs):
        pass

    def can_prepare_commit(self, *args, **kwargs):
        pass

    def prepare_commit(self, *args, **kwargs):
        pass

    def commit(self, *args, **kwargs):
        pass


class TransactionsManager(object):
    """ Coordinate several transaction handlers with a two phase commit protocol.
        You must add transaction handler to the transactions manager before beggining the transactions.

        Then the transaction manager must be used as a context manager:

        trm = TransactionsManager()
        with trm.begin():
            trm.execute()
            trm.commit()
    """

    def __init__(self):
        self._transaction_handlers = []
        self._begun = False
        self._already_rollbacked = False
        self.exceptions_encountered = []

    def add_transaction_handler(self, transaction_handler):
        if self._begun:
            # Can't add transaction handler after transaction have began
            raise TransactionException("Transactions have begun!")
        self._transaction_handlers.append(transaction_handler)

    @contextmanager
    def begin(self):
        self._already_rollbacked = False
        self.exceptions_encountered = []
        self._begun = True
        for transaction_handler in self._transaction_handlers:
            transaction_handler.begin()
        try:
            yield
        except Exception as e:
            # Exception may have been already added to self.exceptions_encountered
            # if rollback has been already called for example.
            if not self.exceptions_encountered or self.exceptions_encountered[-1][0] != e:
                self.exceptions_encountered.append((e, traceback.format_exc(e)))
            if self._already_rollbacked:
                # "raise WeAreDoomedException from" en python3
                exceptions_encountered = [traceback_txt for exc, traceback_txt in self.exceptions_encountered]
                raise WeAreDoomedException("Transactions already rollbacked", exceptions_encountered)
            else:
                try:
                    self.rollback()
                except Exception as rlb_e:
                    # rlb_e should have already been added to self._exceptions_encountered.
                    if not self.exceptions_encountered or self.exceptions_encountered[-1][0] != rlb_e:
                        self.exceptions_encountered.append((rlb_e, traceback.format_exc(rlb_e)))
                    exceptions_encountered = [traceback_txt for exc, traceback_txt in self.exceptions_encountered]
                    raise WeAreDoomedException("Transactions rollbacking failed.", exceptions_encountered)
            raise

    def execute(self):
        """ Will call execute on all transaction handlers """
        if not self._begun:
            raise TransactionException("Transactions have not begun!")
        for transaction_handler in self._transaction_handlers:
            transaction_handler.execute()

    def rollback(self):
        """ Will call rollback on all transaction handlers. All exceptions encountered during rollbacks will be saved in
            self.exceptions_encountered and last exception will be re-raised. So, all rollbacks are called even if one failed.
        """
        if not self._begun:
            raise TransactionException("Transactions have not begun!")
        self._already_rollbacked = True
        last_exc = None
        for transaction_handler in self._transaction_handlers:
            try:
                transaction_handler.rollback()
            except Exception as e:
                self.exceptions_encountered.append((e, traceback.format_exc(e)))
                last_exc = e
        if last_exc:
            raise last_exc

    def commit(self):
        if not self._begun:
            raise TransactionException("Transactions have not begun!")
        # Two phase commit.
        # Prepare commit for all transactions.
        prepare_commit_trs = [transaction_handler for transaction_handler in self._transaction_handlers
                              if transaction_handler.can_prepare_commit()]
        if any(not transaction_handler.prepare_commit() for transaction_handler in prepare_commit_trs):
            # Prepare commit has failed. We rollback.
            self.rollback()
            return
        # All commit have been prepared.
        # We commit first those who can't be prepared.
        no_prepare_commit_trs = [transaction_handler for transaction_handler in self._transaction_handlers
                                 if not transaction_handler.can_prepare_commit()]
        for transaction_handler in no_prepare_commit_trs:
            transaction_handler.commit()
        for transaction_handler in prepare_commit_trs:
            transaction_handler.commit()
        # FYI: since commit are done inside the begin context managing, if a commit fails, even the last, rollback will be done.


class PipelineTransactionHandler(TransactionHandler):
    """ A pipeline transaction is a transaction that does its pipelined actions directly.
        There is no commit possible in this transaction. If we must rollback, the pipeline is done backward to undo things.
    """
    # TODO: add a function to retrieve the name of the pipeline

    def __init__(self, actions_pipeline):
        self._actions_pipeline = None
        self.actions_pipeline = actions_pipeline  # Will call property setter.

    @property
    def actions_pipeline(self):
        return self._actions_pipeline

    @actions_pipeline.setter
    def actions_pipeline(self, actions_pipeline):
        self._actions_pipeline = actions_pipeline
        # To reduce stack trace deepness.
        self.execute = self.actions_pipeline.do
        self.rollback = self.actions_pipeline.undo

    def can_prepare_commit(self):
        # Since a pipeline transaction does not do commit, the prepare-commit->commit phase is reliable
        # and we can assure transaction manager that the commit will not fail.
        # In fact, the pipeline could have a method to checks that everything is correct in the prepare commit phase.
        return True

    def prepare_commit(self):
        return True
