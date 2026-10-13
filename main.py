import sys
import os

# Ensure current directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from core.db import init_db
from ui.styles import DARK_THEME_QSS
from ui.main_window import MainWindow

def main():
    # High DPI scaling attributes
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # Initialize SQLite database
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("GitHub Repository Manager")
    app.setOrganizationName("GitHubAutomate")

    # Apply modern Dark developer stylesheet
    app.setStyleSheet(DARK_THEME_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
