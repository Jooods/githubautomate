# Modern Developer Theme Stylesheet (GitHub Dark Aesthetic)

DARK_THEME_QSS = """
/* Global Application Styles */
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #090d16;
}

/* ToolBar & MenuBar */
QMenuBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 4px;
}
QMenuBar::item {
    background-color: transparent;
    padding: 6px 10px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #21262d;
    color: #58a6ff;
}

QMenu {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #1f6feb;
    color: #ffffff;
}

/* Panels, Frames, Cards */
QFrame.card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}

QFrame#sidebar {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}

QFrame#header {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 8px 16px;
}

/* Inputs & Form Controls */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e6edf3;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #58a6ff;
    background-color: #0d1117;
}

QComboBox {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e6edf3;
    min-width: 100px;
}
QComboBox:hover {
    background-color: #30363d;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: none;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
    border-radius: 6px;
}

/* Buttons */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #161b22;
}
QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

QPushButton.primary {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
    font-weight: 600;
}
QPushButton.primary:hover {
    background-color: #2ea043;
    border-color: #3fb950;
}
QPushButton.primary:pressed {
    background-color: #1d722e;
}

QPushButton.accent {
    background-color: #1f6feb;
    color: #ffffff;
    border: 1px solid #388bfd;
    font-weight: 600;
}
QPushButton.accent:hover {
    background-color: #388bfd;
}

QPushButton.danger {
    background-color: #21262d;
    color: #f85149;
    border: 1px solid #da3633;
}
QPushButton.danger:hover {
    background-color: #b62324;
    color: #ffffff;
}

/* Table View */
QTableWidget, QTableView {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    gridline-color: #21262d;
    color: #e6edf3;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #30363d;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
}
QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #161b22;
}
QTableWidget::item:selected {
    background-color: #1f3764;
    color: #ffffff;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #30363d;
    background-color: #0d1117;
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    border: 1px solid #30363d;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 4px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #0d1117;
    color: #58a6ff;
    border-color: #30363d;
    border-top: 2px solid #58a6ff;
}
QTabBar::tab:hover:!selected {
    background-color: #21262d;
    color: #c9d1d9;
}

/* ScrollBar */
QScrollBar:vertical {
    border: none;
    background: #0d1117;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #484f58;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #0d1117;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
    min-width: 20px;
    border-radius: 5px;
}

/* Progress Bar */
QProgressBar {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #238636;
    border-radius: 3px;
}

/* Labels & Status */
QLabel {
    color: #c9d1d9;
}
QLabel.title {
    font-size: 16px;
    font-weight: 600;
    color: #f0f6fc;
}
QLabel.subtitle {
    font-size: 12px;
    color: #8b949e;
}
QLabel.badge {
    background-color: #21262d;
    color: #8b949e;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
QLabel.badge-public {
    background-color: #172b4d;
    color: #58a6ff;
    border: 1px solid #1f6feb;
}
QLabel.badge-private {
    background-color: #2d1d24;
    color: #f85149;
    border: 1px solid #da3633;
}
QLabel.badge-semver {
    background-color: #261f38;
    color: #bc8cff;
    border: 1px solid #8957e5;
}

/* Splitter */
QSplitter::handle {
    background-color: #21262d;
}
QSplitter::handle:hover {
    background-color: #58a6ff;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    color: #c9d1d9;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #30363d;
    background-color: #161b22;
}
QCheckBox::indicator:checked {
    background-color: #1f6feb;
    border-color: #58a6ff;
}
"""
