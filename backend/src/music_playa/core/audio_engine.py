class AudioEngine:
    """Placeholder for the SoLoud wrapper.

    The mock player does not call this class. A later version will load
    libsoloud, enable visualization, and stream audio through WavStream.
    """

    def __init__(self) -> None:
        self._ready = False
