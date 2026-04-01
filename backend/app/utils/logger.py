import logging
import sys


FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"





def _setup_root_logger():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if root.handlers:
        root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(FORMAT))
    root.addHandler(handler)
    logging.captureWarnings(True)


_setup_root_logger()


def get_logger(name):
    return logging.getLogger(name) if name else logging.getLogger()
