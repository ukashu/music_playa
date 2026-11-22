from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Transport(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        transport_row = QHBoxLayout()
        self.play = QPushButton("Play")
        self.pause = QPushButton("Pause")
        self.stop = QPushButton("Stop")
        self.previous = QPushButton("Previous")
        self.next = QPushButton("Next")
        for button in (self.play, self.pause, self.stop, self.previous, self.next):
            transport_row.addWidget(button)

        test_row = QHBoxLayout()
        self.mode = QPushButton("Mode: In Order")
        self.seek_end = QPushButton("Seek 3s from End")
        self.volume_down = QPushButton("Volume -")
        self.volume_up = QPushButton("Volume +")
        self.volume_label = QLabel("Volume: 100%")
        for widget in (
            self.mode,
            self.seek_end,
            self.volume_down,
            self.volume_up,
            self.volume_label,
        ):
            test_row.addWidget(widget)

        layout.addLayout(transport_row)
        layout.addLayout(test_row)
