# -*- coding: utf-8 -*-

"""
Streamers are class that takes infos from actions or pipelines and logs it.
"""

import logging
import traceback

logger = logging.getLogger("pysyphe")
logger.setLevel(logging.INFO)


class InfoStreamer(object):
    """ Interface for streamers """

    def send_info(self, **kwargs):
        pass


class HumanReadableActionsLogger(InfoStreamer):
    """ Streamer that logs for humans. """

    def send_info(self, **kwargs):
        log_txt = []
        if "action_name" in kwargs:
            if "begin" in kwargs:
                log_txt.append("Do")
            elif "end" in kwargs and "exc" not in kwargs:
                log_txt.append("Successfull end of")
            elif "exc" in kwargs:
                log_txt.append("Failure of")
            elif "simul" in kwargs:
                log_txt.append("Simulation of")
            log_txt.append("{action_name}")
            if "rollback_of" in kwargs:
                log_txt.append("(rollback of {rollback_of})")
            if "state" in kwargs:
                log_txt.append("with state: {state}")
            if "exc" in kwargs:
                log_txt.append("- Exception: {exc}: {traceback}")
                kwargs["traceback"] = traceback.format_exc()

        if log_txt:
            logger.info(" ".join(log_txt).format(**kwargs))


class ActionsLoggerForSimulation(InfoStreamer):
    """ Streamer that format logs for further simulation. """

    def send_info(self, **kwargs):
        # TODO: TO BE IMPLEMENTED
        pass
