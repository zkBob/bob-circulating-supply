import logging
from functools import cache

uvicorn_logger = logging.getLogger("uvicorn.error")

FORMAT = "%(levelname)s:     %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)

@cache
class LoggerProvider():
    __switch_to_uvicorn: bool = False

    def switch_to_uvicorn(self):
        self.__switch_to_uvicorn = True

    def info(self, *args, **kwargs):
        if self.__switch_to_uvicorn:
            uvicorn_logger.info(*args, **kwargs)
        else:
            logging.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        if self.__switch_to_uvicorn:
            uvicorn_logger.warning(*args, **kwargs)
        else:
            logging.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        if self.__switch_to_uvicorn:
            uvicorn_logger.error(*args, **kwargs)
        else:
            logging.error(*args, **kwargs)

info = LoggerProvider().info
warning = LoggerProvider().warning
error = LoggerProvider().error
