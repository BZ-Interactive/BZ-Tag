from .bztagerror import SorterError

_STYLES = {}


def by_filename(name):
    """Case-insensitive filename key; '01.Intro.mp3' sorts before '02.Track.mp3'."""
    return name.lower()


_STYLES["filename"] = by_filename


def by_track_number(path):
    """Skeleton — needs core.metadata.read_tags to compare the 'N' of 'N/T'.

    Registered now so the style name is discoverable and testable; becomes
    a real key function once metadata exists.
    """
    raise SorterError("track_number sort is not implemented yet")


_STYLES["track_number"] = by_track_number


def sort(paths, how="filename"):
    """Sort `paths` by the registered style `how`; a new list is returned."""
    key = _STYLES.get(how)
    if key is None:
        raise SorterError(f"unknown sort style: {how}")
    return sorted(paths, key=key)
