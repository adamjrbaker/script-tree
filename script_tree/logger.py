""" Custom Logger"""

# Python
import logging


def set_logger():
    logger = logging.getLogger('Script-Tree')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(name)s %(levelname)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # prevent logging from bubbling up to maya's logger
    logger.propagate = 0

    return logger


log = set_logger()
