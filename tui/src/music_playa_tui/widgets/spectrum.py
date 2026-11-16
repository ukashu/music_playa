from textual.widgets import Label


class SpectrumPlaceholder(Label):
    def __init__(self, band_count: int) -> None:
        super().__init__(f"spectrum placeholder ({band_count} bands)")
