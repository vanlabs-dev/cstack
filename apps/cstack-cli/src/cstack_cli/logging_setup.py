import logging

from pythonjsonlogger.json import JsonFormatter


def configure_logging(level: str) -> None:
    """Install a JSON-formatted stderr handler on the root logger.

    Library code uses ``logging.getLogger(__name__)`` and stays silent until
    the CLI entrypoint calls this function. Tests can call it with a higher
    level to suppress noise.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
