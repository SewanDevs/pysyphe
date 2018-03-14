# -*- coding: utf-8 -*-

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
        If the probability of a fail of the commit phase after a successfull commit preparation is high, then the transaction is not reliable.

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
        self._rollback_tried = False

    def add_transaction_handler(self, transaction_handler):
        if self._begun:
            # Can't add transaction handler after transaction have began
            raise Exception("Transactions have begun!")
        self._transaction_handlers.append(transaction_handler)

    @contextmanager
    def begin(self):
        self._rollback_tried = False
        self._begun = True
        for transaction_handler in self._transaction_handlers:
            transaction_handler.begin()
        try:
            yield
        except Exception as e:
            # TODO: Find a solution to do not print exception if it has already been printed by actionLogger.
            print("Transactions failed: {}".format(traceback.format_exc()))
            if self._rollback_tried:
                # "raise WeAreDoomed from" en python3
                # Don't know what we really could do in this case ?!?
                raise Exception( "We are doomed.")
            else:
                try:
                    self.rollback()
                except Exception as e:
                    # TODO: Implement a raise from because it's really usefull for debugging.
                    raise Exception( "We are doomed: {}".format(e))
            raise

    def execute(self):
        if not self._begun:
            raise Exception("Transactions have not begun!")
        for transaction_handler in self._transaction_handlers:
            transaction_handler.execute()

    def rollback(self):
        if not self._begun:
            raise Exception("Transactions have not begun!")
        self._rollback_tried = True
        for transaction_handler in self._transaction_handlers:
            transaction_handler.rollback()

    def commit(self):
        if not self._begun:
            raise Exception("Transactions have not begun!")
        # Two phase commit.
        # Prepare commit for all transactions.
        prepare_commit_trs = [ transaction_handler for transaction_handler in self._transaction_handlers
                               if transaction_handler.can_prepare_commit() ]
        if any( not transaction_handler.prepare_commit() for transaction_handler in prepare_commit_trs ):
            # Prepare commit has failed. We rollback.
            self.rollback()

        # All commit have been prepared.
        # We commit first those who can't be prepared.
        no_prepare_commit_trs = [ transaction_handler for transaction_handler in self._transaction_handlers
                                  if not transaction_handler.can_prepare_commit() ]
        for transaction_handler in no_prepare_commit_trs:
            transaction_handler.commit()

        for transaction_handler in prepare_commit_trs:
            transaction_handler.commit()


class PipelineTransactionHandler(TransactionHandler):
    """ A pipeline transaction is a transaction that does its pipelined actions directly.
        There is no commit possible in this transaction. If we must rollback, the pipeline is done backward to undo things.
    """
    #TODO: add a function to retrieve the name of the pipeline

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
