from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class Transport(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        self.play = QPushButton("Play")
        self.pause = QPushButton("Pause")
        self.previous = QPushButton("Previous")
        self.next = QPushButton("Next")
        for button in (self.play, self.pause, self.previous, self.next):
            layout.addWidget(button)
