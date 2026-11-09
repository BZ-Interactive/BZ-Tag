import os

from .bztagerror import ScanError
from .sorter import sort

_SUFFIX = ".mp3"


def scan(directory="."):
    """Return .mp3 paths directly inside `directory`, filename-sorted.

    Recursive scanning is not supported.
    """
    if not os.path.isdir(directory):
        raise ScanError(f"no such directory: {directory}")

    names = []
    for name in os.listdir(directory):
        if not name.lower().endswith(_SUFFIX):
            continue
        if not os.path.isfile(os.path.join(directory, name)):
            continue
        names.append(name)

    return [os.path.join(directory, name) for name in sort(names)]
