_BANDS = 256


class SilentVisualizer:
    def bands(self) -> list[float]:
        return [0.0] * _BANDS

    def wave(self) -> list[float]:
        return [0.0] * _BANDS
