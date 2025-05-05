# styles.py
MAIN_STYLE = '''
QWidget {
    background: #f7f8fa;
    color: #222;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 9.5pt;
}
QMainWindow::separator, QSplitter::handle {
    background: #e0e0e0;
}
QPushButton {
    background: #f0f0f3;
    border: 1px solid #d0d0d0;
    border-radius: 8px;
    padding: 4px 8px;
    margin: 2px;
    font-weight: 500;
    /* min-width and max-width removed to prevent text cutoff */
}
QPushButton:hover {
    background: #e6e6eb;
    border: 1px solid #b0b0b0;
}
QPushButton:pressed {
    background: #d0d0d5;
}
QMenuBar::item {
    padding: 4px 16px;
}
QMenuBar::item:selected {
    background: #e6e6eb;
    color: #222;
    border-radius: 4px;
    /* Add cursor pointer for menu bar items */
    cursor: pointer;
}
QMenu::item {
    padding: 4px 24px 4px 24px;
}
QMenu::item:selected {
    background: #e6e6eb;
    color: #222;
    border-radius: 4px;
    /* Add cursor pointer for menu items */
    cursor: pointer;
}
QSlider::groove:horizontal {
    border: 1px solid #bbb;
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #fff;
    border: 1px solid #aaa;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #b3d1ff;
    border-radius: 4px;
}
QListWidget {
    background: #fafbfc;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 4px;
}
QStatusBar {
    background: #f0f0f3;
    border-top: 1px solid #e0e0e0;
    font-size: 9pt;
}
QLabel {
    font-size: 9.5pt;
}
QProgressBar {
    border: 1px solid #b0b0b0;
    border-radius: 8px;
    background: #f0f0f3;
    height: 14px;
    text-align: center;
}
QProgressBar::chunk {
    background: #4a90e2;
    border-radius: 8px;
}
'''

SEGMENT_LIST_STYLE = '''
QListWidget {
    font-size: 8pt;
    background: #fafbfc;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 4px;
}
'''

LOG_TEXTEDIT_STYLE = '''
QTextEdit {
    font-size: 8pt;
    background: rgba(245, 245, 250, 0.95);
    color: #222;
    font-family: "Segoe UI", "Arial", sans-serif;
    border-radius: 10px;
    border: 1px solid #d0d0d0;
    padding: 10px;
    margin: 0px;
}
'''

# Add reusable style variables for section titles, main buttons, and disabled buttons
SECTION_TITLE_STYLE = 'font-size: 8.5pt; font-weight: bold; margin-bottom: 0px;'
MAIN_BUTTON_STYLE = 'font-size: 8.5pt; font-weight: bold;'
DISABLED_BUTTON_STYLE = 'background: #e0e0e0; color: #aaa; border: 1px solid #ccc;'
LOAD_BTN_STYLE = 'font-size: 8.5pt; padding: 2px 8px;'
