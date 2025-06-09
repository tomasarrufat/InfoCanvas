import os
import sys
import pytest
from PyQt5.QtWidgets import QApplication

class DummyQtBot:
    def addWidget(self, widget):
        widget.show()

@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def qtbot(qapp):
    return DummyQtBot()
