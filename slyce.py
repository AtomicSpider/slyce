import sys
import os

try:
    # PyInstaller: _MEIPASS is the temp folder with bundled files
    base_path = sys._MEIPASS
except AttributeError:
    # Development: use script directory
    base_path = os.path.dirname(os.path.abspath(__file__))

vlc_dir = os.path.join(base_path, 'bin', 'vlc')
vlc_plugins = os.path.join(vlc_dir, 'plugins')
libvlc_path = os.path.join(vlc_dir, 'libvlc.dll')

os.environ['VLC_PLUGIN_PATH'] = vlc_plugins
os.environ['PYTHON_VLC_LIB_PATH'] = libvlc_path
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(vlc_dir)

import vlc

# Debug: print VLC environment variables
print('PATH:', os.environ['PATH'])
print('VLC_PLUGIN_PATH:', os.environ.get('VLC_PLUGIN_PATH'))

import subprocess
import logging
import logging.handlers
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel, QFileDialog, QVBoxLayout, QHBoxLayout, QMessageBox, QListWidget, QListWidgetItem, QSlider, QStatusBar, QSplitter, QMenuBar, QAction, QMenu, QDialog, QFormLayout, QLineEdit, QCheckBox, QComboBox, QProgressBar, QStyleFactory, QTextEdit, QShortcut, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QTime, QDateTime, QObject
from PyQt5.QtGui import QPainter, QColor, QPixmap, QIcon, QKeySequence
from styles import MAIN_STYLE, SEGMENT_LIST_STYLE, LOG_TEXTEDIT_STYLE, SECTION_TITLE_STYLE, MAIN_BUTTON_STYLE, DISABLED_BUTTON_STYLE, LOAD_BTN_STYLE

FFMPEG = os.path.join(base_path, 'bin', 'ffmpeg.exe')

# Helper for subprocess creationflags to suppress console on Windows
subprocess_flags = 0
if sys.platform == "win32":
    subprocess_flags = subprocess.CREATE_NO_WINDOW

def setup_logger():
    logger = logging.getLogger("Slyce")
    logger.setLevel(logging.DEBUG)
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(base_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'slyce.log')
    handler = logging.handlers.TimedRotatingFileHandler(log_file, when='midnight', backupCount=7, encoding='utf-8')
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)
    return logger

class Segment:
    def __init__(self, start, end):
        self.start = start
        self.end = end
    def __str__(self):
        return f"{self.format_time(self.start)} - {self.format_time(self.end)}"
    @staticmethod
    def format_time(ms):
        s = int(ms / 1000)
        return f"{s//3600:02}:{(s%3600)//60:02}:{s%60:02}"

class SegmentSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.segments = []  # List of (start, end) tuples in ms
        self.colors = [QColor(255, 200, 0, 120), QColor(0, 200, 255, 120), QColor(200, 255, 0, 120), QColor(255, 0, 200, 120), QColor(200, 0, 255, 120), QColor(0, 255, 200, 120)]
        self.temp_marker = None  # (start, end) or (start, None) or (None, end)

    def set_segments(self, segments):
        self.segments = [(s.start, s.end) for s in segments]
        self.update()

    def set_temp_marker(self, start=None, end=None):
        self.temp_marker = (start, end)
        self.update()

    def clear_temp_marker(self):
        self.temp_marker = None
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.maximum() == 0:
            return
        painter = QPainter(self)
        bar_rect = self.rect()
        # Draw segments
        for idx, (start, end) in enumerate(self.segments):
            x1 = int(bar_rect.width() * start / self.maximum())
            x2 = int(bar_rect.width() * end / self.maximum())
            highlight_rect = bar_rect.adjusted(x1, 0, -(bar_rect.width()-x2), 0)
            color = self.colors[idx % len(self.colors)]
            painter.fillRect(highlight_rect, color)
        # Draw temp marker
        if self.temp_marker:
            start, end = self.temp_marker
            marker_color = QColor(255, 0, 0, 180)
            if start is not None:
                x = int(bar_rect.width() * start / self.maximum())
                painter.setPen(marker_color)
                painter.drawLine(x, 0, x, bar_rect.height())
            if end is not None:
                x = int(bar_rect.width() * end / self.maximum())
                painter.setPen(QColor(0, 255, 0, 180))
                painter.drawLine(x, 0, x, bar_rect.height())
        painter.end()

class ExportThread(QThread):
    status_update = pyqtSignal(str)
    export_done = pyqtSignal(bool, str)

    def __init__(self, segments, videoPath, outfiles, find_nearest_keyframe, find_next_keyframe, logger):
        super().__init__()
        self.segments = segments
        self.videoPath = videoPath
        self.outfiles = outfiles
        self.find_nearest_keyframe = find_nearest_keyframe
        self.find_next_keyframe = find_next_keyframe
        self.logger = logger

    def run(self):
        try:
            for i, seg in enumerate(self.segments):
                user_start_sec = seg.start / 1000
                user_end_sec = seg.end / 1000
                actual_start_sec = self.find_nearest_keyframe(user_start_sec)
                actual_end_sec = self.find_next_keyframe(user_end_sec)
                duration = actual_end_sec - actual_start_sec
                outfile = self.outfiles[i]
                cmd = [
                    FFMPEG, '-y', '-ss', str(actual_start_sec), '-i', self.videoPath,
                    '-t', str(duration), '-c', 'copy', outfile
                ]
                self.status_update.emit(f"Exporting segment {i+1}/{len(self.segments)}...")
                self.logger.info(f"Exporting segment {i+1}: {cmd}")
                try:
                    subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=subprocess_flags)
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Failed to export {outfile}: {e.output.decode()}")
                    self.export_done.emit(False, f"Failed to export {os.path.basename(outfile)}\n{e.output.decode()}")
                    return
            self.export_done.emit(True, f"Exported {len(self.segments)} segments.")
        except Exception as e:
            self.logger.error(f"Export error: {e}")
            self.export_done.emit(False, str(e))

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        layout = QFormLayout(self)
        self.output_folder = QLineEdit()
        self.filename_pattern = QLineEdit('{basename}_{index}')
        self.reencode = QCheckBox('Re-encode (frame-accurate)')
        layout.addRow('Output Folder:', self.output_folder)
        layout.addRow('Filename Pattern:', self.filename_pattern)
        layout.addRow('', self.reencode)
        self.setLayout(layout)
        # Set cursor to pointing hand on all dialog buttons
        for attr in dir(self):
            if attr.endswith('Btn') or attr.endswith('Button'):
                btn = getattr(self, attr, None)
                if isinstance(btn, QPushButton):
                    btn.setCursor(Qt.PointingHandCursor)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('About')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Slyce App\n(c) 2025 Sanat Dutta'))
        self.setLayout(layout)
        # Set cursor to pointing hand on all dialog buttons
        for attr in dir(self):
            if attr.endswith('Btn') or attr.endswith('Button'):
                btn = getattr(self, attr, None)
                if isinstance(btn, QPushButton):
                    btn.setCursor(Qt.PointingHandCursor)

class ThumbnailBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnails = []  # List of QPixmap
        self.setMinimumHeight(60)
    def set_thumbnails(self, pixmaps):
        self.thumbnails = pixmaps
        self.update()
    def paintEvent(self, event):
        if not self.thumbnails:
            return
        painter = QPainter(self)
        w = self.width() // len(self.thumbnails)
        for i, pix in enumerate(self.thumbnails):
            painter.drawPixmap(i * w, 0, w, self.height(), pix)
        painter.end()

class SlyceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slyce")
        self.setGeometry(100, 100, 1280, 720)
        self.setWindowIcon(QIcon(os.path.join('assets', 'slyce.ico')))
        self.setMinimumWidth(600)  # Reduced for more flexibility
        self.setMinimumHeight(400)
        self.logger = setup_logger()
        self.logger.info("App started.")
        # VLC instance and player
        self.vlc_instance = vlc.Instance()
        if self.vlc_instance is None:
            raise RuntimeError("Failed to create VLC instance. Check if VLC DLLs and plugins are present in the bin/vlc folder and environment variables are set correctly.")
        self.vlc_player = self.vlc_instance.media_player_new()
        # Video frame for VLC
        self.video_frame = QWidget(self)
        self.video_frame.setStyleSheet("background: black;")
        self.playPauseBtn = QPushButton('Play/Pause (Space)')
        self.muteBtn = QPushButton('Mute (M)')
        self.markStartBtn = QPushButton('Start (S)')
        self.markEndBtn = QPushButton('End (E)')
        self.undoBtn = QPushButton('Undo (Ctrl+Z)')
        self.redoBtn = QPushButton('Redo (Ctrl+Y)')
        self.exportBtn = QPushButton('Export (Ctrl+E)')
        self.stopExportBtn = QPushButton('Stop Export')
        self.stopExportBtn.setVisible(False)
        self.slider = SegmentSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.infoLabel = QLabel('No video loaded.')
        self.segmentList = QListWidget()
        self.segments = []
        self.undo_stack = []
        self.redo_stack = []
        self.currentStart = None
        self.videoPath = None
        self.duration = 0
        self.duration_timer = QTimer(self)
        self.duration_timer.setInterval(500)
        self.duration_timer.timeout.connect(self.poll_duration)
        self.theme = 'light'
        self.progressBar = QProgressBar()
        self.progressBar.setVisible(False)
        self.thumbnailBar = ThumbnailBar()
        self.settings = {'output_folder': '', 'filename_pattern': '{basename}_{index}', 'reencode': False}
        self.init_menu()
        self.init_ui()
        self.connect_signals()
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_slider_highlight)
        self.timer.timeout.connect(self.update_slider_position)
        self.timer.start()
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Ready')
        # Disable media buttons at startup (greyed out)
        for btn in [self.playPauseBtn, self.muteBtn, self.markStartBtn, self.markEndBtn, self.undoBtn, self.redoBtn, self.exportBtn, self.stopExportBtn]:
            btn.setEnabled(False)
            btn.setStyleSheet(DISABLED_BUTTON_STYLE)

    def init_menu(self):
        menubar = self.menuBar() if hasattr(self, 'menuBar') else QMenuBar(self)
        fileMenu = menubar.addMenu('File')
        exitAct = QAction('Exit', self)
        exitAct.triggered.connect(self.close)
        fileMenu.addAction(exitAct)
        # Add About directly to the menubar
        aboutAct = QAction('About', self)
        aboutAct.triggered.connect(self.open_about)
        menubar.addAction(aboutAct)
        # Add Buy me a Coffee
        buyCoffeeAct = QAction('Buy me a Coffee !!', self)
        buyCoffeeAct.triggered.connect(lambda: os.startfile('https://www.paypal.com/paypalme/atomicspider'))
        menubar.addAction(buyCoffeeAct)
        self.setMenuBar(menubar)
        # --- Event filter for menu bar to show pointing hand cursor ---
        class MenuCursorEventFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == event.Enter:
                    QApplication.setOverrideCursor(Qt.PointingHandCursor)
                elif event.type() == event.Leave:
                    QApplication.restoreOverrideCursor()
                return False
        self._menu_cursor_filter = MenuCursorEventFilter(self)
        menubar.installEventFilter(self._menu_cursor_filter)

    def init_ui(self):
        # Video area
        self.video_frame.setMinimumWidth(320)  # Reduced for split screen usability
        self.video_frame.setMinimumHeight(200)
        # Controls
        controlLayout = QHBoxLayout()
        controlLayout.insertStretch(0, 1)
        controlLayout.addWidget(self.playPauseBtn)
        controlLayout.addWidget(self.muteBtn)
        controlLayout.addWidget(self.markStartBtn)
        controlLayout.addWidget(self.markEndBtn)
        controlLayout.addWidget(self.undoBtn)
        controlLayout.addWidget(self.redoBtn)
        controlLayout.addWidget(self.exportBtn)
        controlLayout.addWidget(self.stopExportBtn)
        controlLayout.addStretch(1)
        # Make controlLayout buttons expand if space is available
        for btn in [self.playPauseBtn, self.muteBtn, self.markStartBtn, self.markEndBtn, self.undoBtn, self.redoBtn, self.exportBtn, self.stopExportBtn]:
            btn.setSizePolicy(btn.sizePolicy().Expanding, btn.sizePolicy().verticalPolicy())
        # Set cursor to pointing hand on all buttons
        for btn in [self.playPauseBtn, self.muteBtn, self.markStartBtn, self.markEndBtn, self.undoBtn, self.redoBtn, self.exportBtn, self.stopExportBtn]:
            btn.setCursor(Qt.PointingHandCursor)
        # Style for main control buttons
        for btn in [self.playPauseBtn, self.muteBtn, self.markStartBtn, self.markEndBtn, self.undoBtn, self.redoBtn, self.exportBtn, self.stopExportBtn]:
            btn.setStyleSheet(MAIN_BUTTON_STYLE)
        # Add global shortcuts for all main actions
        self.playPauseShortcut = QShortcut(QKeySequence('Space'), self)
        self.playPauseShortcut.activated.connect(self.toggle_play_pause)
        self.muteShortcut = QShortcut(QKeySequence('M'), self)
        self.muteShortcut.activated.connect(self.toggle_mute)
        self.undoShortcut = QShortcut(QKeySequence('Ctrl+Z'), self)
        self.undoShortcut.activated.connect(self.undo_segment)
        self.redoShortcut = QShortcut(QKeySequence('Ctrl+Y'), self)
        self.redoShortcut.activated.connect(self.redo_segment)
        self.exportShortcut = QShortcut(QKeySequence('Ctrl+E'), self)
        self.exportShortcut.activated.connect(self.export_segments)
        # Add global shortcuts for Start (S) and End (E)
        self.startShortcut = QShortcut(QKeySequence('S'), self)
        self.startShortcut.activated.connect(self.mark_start)
        self.endShortcut = QShortcut(QKeySequence('E'), self)
        self.endShortcut.activated.connect(self.mark_end)
        # Remove setShortcut from all buttons to avoid focus issues
        self.playPauseBtn.setShortcut(QKeySequence())
        self.muteBtn.setShortcut(QKeySequence())
        self.undoBtn.setShortcut(QKeySequence())
        self.redoBtn.setShortcut(QKeySequence())
        self.exportBtn.setShortcut(QKeySequence())
        self.markStartBtn.setShortcut(QKeySequence())
        self.markEndBtn.setShortcut(QKeySequence())
        self.stopExportBtn.setShortcut(QKeySequence())
        # Video + seekbar
        videoLayout = QVBoxLayout()
        videoLayout.addWidget(self.video_frame)
        videoLayout.addWidget(self.slider)
        # Segments and logs (side by side, no splitter)
        segLogLayout = QHBoxLayout()
        segLogLayout.setContentsMargins(0, 0, 0, 0)
        segLogLayout.setSpacing(16)
        segWidget = QWidget()
        segLayout = QVBoxLayout()
        segLayout.setContentsMargins(0, 0, 0, 0)
        segLayout.setSpacing(4)
        segmentsLabel = QLabel('Segments:')
        segmentsLabel.setStyleSheet(SECTION_TITLE_STYLE)
        segLayout.addWidget(segmentsLabel)
        segLayout.addWidget(self.segmentList)
        segWidget.setLayout(segLayout)
        logWidget = QWidget()
        logLayout = QVBoxLayout()
        logLayout.setContentsMargins(0, 0, 0, 0)
        logLayout.setSpacing(4)
        logsLabel = QLabel('Logs:')
        logsLabel.setStyleSheet(SECTION_TITLE_STYLE)
        self.logTextEdit = QTextEdit()
        logLayout.addWidget(logsLabel)
        logLayout.addWidget(self.logTextEdit)
        logWidget.setLayout(logLayout)
        segLogLayout.addWidget(segWidget, 1)
        segLogLayout.addWidget(logWidget, 1)
        segLogContainer = QWidget()
        segLogContainer.setFixedHeight(220)
        segLogContainer.setLayout(segLogLayout)
        # Playlist widget
        self.playlistWidget = QListWidget()
        self.playlistWidget.setObjectName('Videos')
        self.playlistWidget.setAcceptDrops(True)
        self.playlistWidget.setDragDropMode(QListWidget.DropOnly)
        self.playlistWidget.setSelectionMode(QListWidget.SingleSelection)
        self.playlistWidget.setMinimumWidth(180)
        self.playlistWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.playlistWidget.setStyleSheet('''
            QListWidget {
                background: #f4f6fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 6px;
                font-size: 8pt;
            }
        ''')
        playlistWidgetContainer = QWidget()
        playlistLayout = QVBoxLayout()
        topRow = QHBoxLayout()
        playlistLabel = QLabel('Videos:')
        playlistLabel.setStyleSheet(SECTION_TITLE_STYLE)
        self.loadBtn = QPushButton('Load Videos')
        self.loadBtn.setCursor(Qt.PointingHandCursor)
        self.loadBtn.setStyleSheet(LOAD_BTN_STYLE)
        self.loadBtn.clicked.connect(self.open_folder)
        topRow.addWidget(playlistLabel)
        topRow.addStretch(1)
        topRow.addWidget(self.loadBtn)
        playlistLayout.addLayout(topRow)
        playlistLayout.addWidget(self.playlistWidget, stretch=1)
        playlistLayout.setStretch(1, 1)  # Make playlistWidget take all extra vertical space
        playlistWidgetContainer.setLayout(playlistLayout)
        playlistWidgetContainer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        playlistWidgetContainer.setMinimumWidth(120)
        # Right side: everything else
        rightWidget = QWidget()
        rightLayout = QVBoxLayout()
        rightLayout.addLayout(videoLayout)
        rightLayout.addLayout(controlLayout)
        rightLayout.addWidget(segLogContainer)
        rightLayout.addWidget(self.progressBar)
        rightWidget.setLayout(rightLayout)
        rightWidget.setMinimumWidth(350)
        # Main horizontal layout: playlist (left), rest (right)
        mainSplitter = QSplitter(Qt.Horizontal)
        mainSplitter.addWidget(playlistWidgetContainer)
        mainSplitter.addWidget(rightWidget)
        mainSplitter.setStretchFactor(0, 0)
        mainSplitter.setStretchFactor(1, 1)
        mainSplitter.widget(0).setMinimumWidth(120)
        mainSplitter.widget(1).setMinimumWidth(350)
        mainSplitter.setHandleWidth(8)
        container = QWidget()
        mainLayout = QHBoxLayout()
        mainLayout.addWidget(mainSplitter)
        container.setLayout(mainLayout)
        self.setCentralWidget(container)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Ready')
        # Apply styles from styles.py
        self.setStyleSheet(MAIN_STYLE)
        self.segmentList.setStyleSheet(SEGMENT_LIST_STYLE)
        self.logTextEdit.setStyleSheet(LOG_TEXTEDIT_STYLE)

    def connect_signals(self):
        self.playPauseBtn.clicked.connect(self.toggle_play_pause)
        self.muteBtn.clicked.connect(self.toggle_mute)
        self.markStartBtn.clicked.connect(self.mark_start)
        self.markEndBtn.clicked.connect(self.mark_end)
        self.exportBtn.clicked.connect(self.export_segments)
        self.stopExportBtn.clicked.connect(self.stop_export)
        self.undoBtn.clicked.connect(self.undo_segment)
        self.redoBtn.clicked.connect(self.redo_segment)
        self.slider.sliderMoved.connect(self.set_position)
        self.playlistWidget.itemDoubleClicked.connect(self.on_playlist_double_click)

    def playlist_drag_enter_event(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def playlist_drop_event(self, event):
        video_exts = ('.mp4', '.avi', '.mov', '.mkv')
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                for f in os.listdir(path):
                    if f.lower().endswith(video_exts):
                        files.append(os.path.join(path, f))
            elif os.path.isfile(path) and path.lower().endswith(video_exts):
                files.append(path)
        for f in files:
            if not any(self.playlistWidget.item(i).data(Qt.UserRole) == f for i in range(self.playlistWidget.count())):
                item = QListWidgetItem(os.path.basename(f))
                item.setData(Qt.UserRole, f)
                self.playlistWidget.addItem(item)
        if files:
            self.playlistWidget.setCurrentRow(self.playlistWidget.count() - len(files))

    def toggle_play_pause(self):
        if self.vlc_player.is_playing():
            self.vlc_player.pause()
            self.playPauseBtn.setText('Play (Space)')
            self.logger.info("Pause pressed.")
        else:
            self.vlc_player.play()
            self.playPauseBtn.setText('Pause (Space)')
            self.logger.info("Play pressed.")
            if self.duration == 0:
                self.duration_timer.start()

    def toggle_mute(self):
        muted = self.vlc_player.audio_get_mute()
        self.vlc_player.audio_set_mute(not muted)
        if not muted:
            self.muteBtn.setText('Unmute (M)')
        else:
            self.muteBtn.setText('Mute (M)')
        self.logger.info(f"Mute toggled. Now muted: {not muted}")

    def open_file(self):
        self.logger.info("open_file called")
        filePath, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mov *.mkv)")
        self.logger.info(f"Open file dialog result: {filePath}")
        if filePath:
            self.open_video_path(filePath)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            video_exts = ('.mp4', '.avi', '.mov', '.mkv')
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(video_exts)]
            self.playlistWidget.clear()
            for f in files:
                item = QListWidgetItem(os.path.basename(f))
                item.setData(Qt.UserRole, f)
                self.playlistWidget.addItem(item)
            if files:
                self.playlistWidget.setCurrentRow(0)
                self.load_video_from_playlist(0)
            for btn in [self.playPauseBtn, self.muteBtn, self.markStartBtn, self.markEndBtn, self.undoBtn, self.redoBtn, self.exportBtn]:
                btn.setEnabled(True)
                btn.setStyleSheet(MAIN_BUTTON_STYLE)

    def on_playlist_double_click(self, item):
        row = self.playlistWidget.row(item)
        self.playlistWidget.setCurrentRow(row)
        self.load_video_from_playlist(row)
        self.highlight_current_playlist_item(row)

    def highlight_current_playlist_item(self, row):
        for i in range(self.playlistWidget.count()):
            item = self.playlistWidget.item(i)
            if i == row:
                item.setBackground(Qt.yellow)
            else:
                item.setBackground(Qt.white)

    def load_video_from_playlist(self, row):
        item = self.playlistWidget.item(row)
        if item:
            self.open_video_path(item.data(Qt.UserRole))
            self.highlight_current_playlist_item(row)

    def open_video_path(self, filePath):
        # This is a refactored version of open_file that takes a filePath directly (no dialog)
        def short_time():
            return QTime.currentTime().toString('HH:mm:ss')
        def log_user(msg, bold_parts=None, indent=0):
            # Helper to log with consistent timestamp, bold, and optional indent
            t = QTime.currentTime().toString('HH:mm:ss')
            if bold_parts:
                for part in bold_parts:
                    msg = msg.replace(part, f'<b>{part}</b>')
            prefix = '    ' * indent
            self.logTextEdit.append(f"[{t}] {prefix}{msg}")
            self.logTextEdit.moveCursor(self.logTextEdit.textCursor().End)
        if filePath:
            try:
                self.vlc_player.stop()
            except Exception:
                pass
            self.duration_timer.stop()
            self.timer.stop()
            self.videoPath = filePath
            media = self.vlc_instance.media_new(filePath)
            self.vlc_player.set_media(media)
            if sys.platform.startswith('win'):
                self.vlc_player.set_hwnd(int(self.video_frame.winId()))
            self.infoLabel.setText(f"Loaded: {os.path.basename(filePath)}")
            self.segments.clear()
            self.segmentList.clear()
            self.currentStart = None
            self.slider.setValue(0)
            self.slider.set_segments([])
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.get_video_info()
            # --- Video metadata logging ---
            try:
                cmd = [
                    FFMPEG.replace('ffmpeg.exe', 'ffprobe.exe'), '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height,bit_rate,codec_name',
                    '-of', 'default=noprint_wrappers=1', filePath
                ]
                vinfo = subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=subprocess_flags).decode().strip().split('\n')
                vmeta = {}
                for line in vinfo:
                    if '=' in line:
                        k, v = line.split('=', 1)
                        vmeta[k.strip()] = v.strip()
                cmd = [
                    FFMPEG.replace('ffmpeg.exe', 'ffprobe.exe'), '-v', 'error', '-select_streams', 'a:0',
                    '-show_entries', 'stream=codec_name,channels,sample_rate,bit_rate',
                    '-of', 'default=noprint_wrappers=1', filePath
                ]
                ainfo = subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=subprocess_flags).decode().strip().split('\n')
                ameta = {}
                for line in ainfo:
                    if '=' in line:
                        k, v = line.split('=', 1)
                        ameta[k.strip()] = v.strip()
                cmd = [
                    FFMPEG.replace('ffmpeg.exe', 'ffprobe.exe'), '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', filePath
                ]
                duration = float(subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=subprocess_flags).decode().strip())
                video_info = f"{os.path.basename(filePath)} ({vmeta.get('width','?')}x{vmeta.get('height','?')}, {duration:.2f} sec)"
                video_details = f"Video: {vmeta.get('codec_name','?')} | Bitrate: {int(vmeta.get('bit_rate',0))//1000 if vmeta.get('bit_rate','').isdigit() else '?'} kbps; Audio: {ameta.get('codec_name','?')} | Channels: {ameta.get('channels','?')} | Sample Rate: {ameta.get('sample_rate','?')} Hz"
                log_user(f"Video loaded: {video_info}", bold_parts=[os.path.basename(filePath)])
                log_user(video_details, indent=1)
            except Exception as e:
                log_user(f"Video loaded: {os.path.basename(filePath)} (metadata unavailable)", bold_parts=[os.path.basename(filePath)])
            self.duration = 0
            self.update_duration()
            self.show_status(f"Loaded: {os.path.basename(filePath)}")
            self.toggle_play_pause()
            self.timer.start()
            for btn in [self.playPauseBtn, self.muteBtn, self.markStartBtn, self.markEndBtn, self.undoBtn, self.redoBtn, self.exportBtn]:
                btn.setEnabled(True)
                btn.setStyleSheet(MAIN_BUTTON_STYLE)

    def play_video(self):
        self.logger.info("Play pressed.")
        self.vlc_player.play()
        # Start polling for duration after playback starts
        if self.duration == 0:
            self.duration_timer.start()

    def pause_video(self):
        self.logger.info("Pause pressed.")
        self.vlc_player.pause()

    def poll_duration(self):
        dur = self.vlc_player.get_length()
        self.logger.info(f"[poll_duration] VLC reported duration: {dur} ms")
        if dur and dur > 0:
            self.slider.setRange(0, dur)
            self.duration = dur
            self.duration_timer.stop()
            self.logger.info(f"[poll_duration] Duration set: {dur} ms")

    def update_duration(self):
        QTimer.singleShot(500, self._set_duration_from_vlc)

    def _set_duration_from_vlc(self):
        dur = self.vlc_player.get_length()
        self.logger.info(f"VLC reported duration: {dur} ms")
        if dur > 0:
            self.slider.setRange(0, dur)
            self.duration = dur
        else:
            self.logger.warning("Duration not available from VLC.")

    def update_slider_position(self):
        pos = self.vlc_player.get_time()
        if self.duration > 0:
            self.slider.blockSignals(True)
            self.slider.setValue(pos)
            self.slider.blockSignals(False)
        self.slider.set_segments(self.segments)

    def set_position(self, position):
        self.vlc_player.set_time(position)

    def get_video_info(self):
        if not self.videoPath:
            return
        try:
            cmd = [
                FFMPEG.replace('ffmpeg.exe', 'ffprobe.exe'), '-v', 'error', '-show_entries',
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.videoPath
            ]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=subprocess_flags).decode().strip()
            self.infoLabel.setText(self.infoLabel.text() + f" | Duration: {float(output):.2f} sec")
        except Exception as e:
            self.infoLabel.setText(self.infoLabel.text() + f" | Duration: Unknown")

    def mark_start(self):
        pos = self.vlc_player.get_time()
        self.logger.info(f"Mark start at {pos}")
        self.currentStart = pos
        self.slider.set_temp_marker(start=pos, end=None)
        self.show_status(f"Start marked at {Segment.format_time(pos)}. Select end.")

    def mark_end(self):
        if self.currentStart is None:
            self.logger.warning("Mark end pressed without start.")
            self.show_status("Mark start first.")
            box = QMessageBox(QMessageBox.Warning, "Error", "Mark start first.", parent=self)
            self.show_message_box(box)
            return
        end = self.vlc_player.get_time()
        self.slider.set_temp_marker(start=self.currentStart, end=end)
        self.logger.info(f"Mark end at {end}")
        # Edge case: end <= start
        if end <= self.currentStart:
            self.logger.warning(f"End ({end}) <= Start ({self.currentStart})")
            self.show_status("End must be after start.")
            box = QMessageBox(QMessageBox.Warning, "Error", "End must be after start.", parent=self)
            self.show_message_box(box)
            self.slider.clear_temp_marker()
            return
        # Edge case: overlap with existing segments
        for seg in self.segments:
            if not (end <= seg.start or self.currentStart >= seg.end):
                self.logger.warning("Segment overlaps with existing segment.")
                self.show_status("Segment overlaps with existing segment.")
                box = QMessageBox(QMessageBox.Warning, "Error", "Segment overlaps with existing segment.", parent=self)
                self.show_message_box(box)
                self.slider.clear_temp_marker()
                return
        segment = Segment(self.currentStart, end)
        self.undo_stack.append(list(self.segments))
        self.redo_stack.clear()
        self.segments.append(segment)
        self.segmentList.addItem(str(segment))
        self.slider.set_segments(self.segments)
        self.slider.clear_temp_marker()
        self.currentStart = None
        self.show_status(f"Segment added: {segment}")

    def undo_segment(self):
        if self.undo_stack:
            self.redo_stack.append(list(self.segments))
            self.segments = self.undo_stack.pop()
            self.segmentList.clear()
            for seg in self.segments:
                self.segmentList.addItem(str(seg))
            self.slider.set_segments(self.segments)
            self.show_status("Undo performed.")

    def redo_segment(self):
        if self.redo_stack:
            self.undo_stack.append(list(self.segments))
            self.segments = self.redo_stack.pop()
            self.segmentList.clear()
            for seg in self.segments:
                self.segmentList.addItem(str(seg))
            self.slider.set_segments(self.segments)
            self.show_status("Redo performed.")

    def find_nearest_keyframe(self, start_time):
        """
        Use ffprobe to find the nearest keyframe before the given start_time (in seconds).
        Returns the timestamp (in seconds) of the nearest keyframe before start_time.
        """
        try:
            cmd = [
                FFMPEG.replace('ffmpeg.exe', 'ffprobe.exe'), '-v', 'error', '-select_streams', 'v:0',
                '-show_frames', '-show_entries', 'frame=pkt_pts_time,key_frame',
                '-of', 'csv', self.videoPath
            ]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=subprocess_flags).decode()
            keyframes = []
            for line in output.splitlines():
                if ',1' in line:  # key_frame=1
                    parts = line.split(',')
                    if len(parts) >= 3:
                        try:
                            t = float(parts[1])
                            keyframes.append(t)
                        except Exception:
                            continue
            # Find the last keyframe before or at start_time
            keyframes = [t for t in keyframes if t <= start_time]
            if keyframes:
                return max(keyframes)
            else:
                return 0.0
        except Exception as e:
            self.logger.error(f"Failed to find keyframe: {e}")
            return start_time

    def find_next_keyframe(self, end_time):
        """
        Use ffprobe to find the next keyframe after the given end_time (in seconds).
        Returns the timestamp (in seconds) of the next keyframe after end_time.
        If not found, returns end_time.
        """
        try:
            cmd = [
                FFMPEG.replace('ffmpeg.exe', 'ffprobe.exe'), '-v', 'error', '-select_streams', 'v:0',
                '-show_frames', '-show_entries', 'frame=pkt_pts_time,key_frame',
                '-of', 'csv', self.videoPath
            ]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, creationflags=subprocess_flags).decode()
            keyframes = []
            for line in output.splitlines():
                if ',1' in line:  # key_frame=1
                    parts = line.split(',')
                    if len(parts) >= 3:
                        try:
                            t = float(parts[1])
                            keyframes.append(t)
                        except Exception:
                            continue
            # Find the first keyframe after end_time
            after = [t for t in keyframes if t > end_time]
            if after:
                return min(after)
            else:
                return end_time
        except Exception as e:
            self.logger.error(f"Failed to find next keyframe: {e}")
            return end_time

    def export_segments(self):
        def log_user(msg, bold_parts=None, indent=0):
            # Helper to log with consistent timestamp, bold, and optional indent
            t = QTime.currentTime().toString('HH:mm:ss')
            if bold_parts:
                for part in bold_parts:
                    msg = msg.replace(part, f'<b>{part}</b>')
            prefix = '    ' * indent
            self.logTextEdit.append(f"[{t}] {prefix}{msg}")
            self.logTextEdit.moveCursor(self.logTextEdit.textCursor().End)
        self.logger.info("Export segments pressed.")
        if not self.segments or not self.videoPath:
            self.logger.warning("No segments or video loaded.")
            self.show_status("No segments or video loaded.")
            box = QMessageBox(QMessageBox.Warning, "Error", "No segments or video loaded.", parent=self)
            self.show_message_box(box)
            return
        # Confirmation before export
        confirm_box = QMessageBox(QMessageBox.Question, "Confirm Export", f"Export {len(self.segments)} segments?", parent=self)
        confirm_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm_box.setMinimumWidth(400)
        confirm = confirm_box.exec_()
        if confirm != QMessageBox.Yes:
            self.show_status("Export cancelled.")
            return
        # Pause playback if playing
        self._was_playing = self.vlc_player.is_playing()
        if self._was_playing:
            self.vlc_player.pause()
            self.logger.info("Playback paused for export.")
        # Disable all controls and shortcuts
        self.set_controls_enabled(False)
        self.set_shortcuts_enabled(False)
        # During export, enable Stop Export button and set its style to normal
        self.stopExportBtn.setEnabled(True)
        self.stopExportBtn.setStyleSheet(MAIN_BUTTON_STYLE)
        self.progressBar.setVisible(True)
        self.progressBar.setMaximum(len(self.segments))
        self.progressBar.setValue(0)
        base, ext = os.path.splitext(self.videoPath)
        base_name = os.path.basename(base)
        dir_name = os.path.dirname(self.videoPath)
        outfiles = []
        for seg in self.segments:
            start_epoch = int(seg.start)
            end_epoch = int(seg.end)
            outfile = os.path.join(dir_name, f"{base_name}_{start_epoch}-{end_epoch}{ext}")
            outfiles.append(outfile)
        for f in outfiles:
            if os.path.exists(f):
                self.logger.error(f"File exists: {f}")
                self.show_status(f"File exists: {os.path.basename(f)}")
                from PyQt5.QtCore import QDateTime
                now = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
                self.logTextEdit.append(f"[{now}] ERROR: File exists: {os.path.basename(f)}")
                box = QMessageBox(QMessageBox.Critical, "File Exists", f"Cannot export. File exists: {os.path.basename(f)}", parent=self)
                self.show_message_box(box)
                # Reset export state if file exists
                self.set_controls_enabled(True)
                self.set_shortcuts_enabled(True)
                self.stopExportBtn.setEnabled(False)
                self.stopExportBtn.setVisible(False)
                self.progressBar.setVisible(False)
                return
        # During export, disable menu bar, load videos button, and playlist double click
        self.menuBar().setEnabled(False)
        self.loadBtn.setEnabled(False)
        self.playlistWidget.itemDoubleClicked.disconnect()
        # Add log entry for export start
        log_user(f"Export started: {len(self.segments)} segments to {dir_name}", bold_parts=[str(len(self.segments)), dir_name])
        self.show_status("Exporting segments...")
        self.export_thread = ExportThread(
            list(self.segments), self.videoPath, outfiles,
            self.find_nearest_keyframe, self.find_next_keyframe, self.logger
        )
        self.export_thread.status_update.connect(self.on_export_status_update)
        self.export_thread.export_done.connect(self.on_export_done)
        self.export_thread.start()

    def set_controls_enabled(self, enabled):
        for btn in [self.playPauseBtn, self.muteBtn, self.markStartBtn, self.markEndBtn, self.undoBtn, self.redoBtn, self.exportBtn]:
            btn.setEnabled(enabled)
            if enabled:
                btn.setStyleSheet(MAIN_BUTTON_STYLE)
            else:
                btn.setStyleSheet(DISABLED_BUTTON_STYLE)
        self.slider.setEnabled(enabled)
        self.segmentList.setEnabled(enabled)
        self.stopExportBtn.setEnabled(not enabled)
        if enabled:
            self.stopExportBtn.setStyleSheet(MAIN_BUTTON_STYLE)
        else:
            self.stopExportBtn.setStyleSheet(DISABLED_BUTTON_STYLE)
        self.stopExportBtn.setVisible(not enabled)

    def set_shortcuts_enabled(self, enabled):
        for shortcut in [self.playPauseShortcut, self.muteShortcut, self.undoShortcut, self.redoShortcut, self.exportShortcut, self.startShortcut, self.endShortcut]:
            shortcut.setEnabled(enabled)

    def on_export_status_update(self, msg):
        if msg.startswith("Exporting segment"):
            try:
                idx = int(msg.split()[2].split('/')[0])
                self.progressBar.setValue(idx)
            except Exception:
                pass
            # Indent segment export progress
            self.logTextEdit.append(f"    {msg}")
        else:
            self.logTextEdit.append(msg)
        self.logTextEdit.moveCursor(self.logTextEdit.textCursor().End)

    def on_export_done(self, success, msg):
        def log_user(msg, bold_parts=None, indent=0):
            # Helper to log with consistent timestamp, bold, and optional indent
            t = QTime.currentTime().toString('HH:mm:ss')
            if bold_parts:
                for part in bold_parts:
                    msg = msg.replace(part, f'<b>{part}</b>')
            prefix = '    ' * indent
            self.logTextEdit.append(f"[{t}] {prefix}{msg}")
            self.logTextEdit.moveCursor(self.logTextEdit.textCursor().End)
        self.set_controls_enabled(True)
        self.set_shortcuts_enabled(True)
        self.stopExportBtn.setEnabled(False)
        self.stopExportBtn.setVisible(False)
        self.progressBar.setVisible(False)
        # Re-enable menu bar, load videos button, and playlist double click after export
        self.menuBar().setEnabled(True)
        self.loadBtn.setEnabled(True)
        self.playlistWidget.itemDoubleClicked.connect(self.on_playlist_double_click)
        # Resume playback if it was playing before export
        if hasattr(self, '_was_playing') and self._was_playing:
            self.vlc_player.play()
            self.logger.info("Playback resumed after export.")
        if success:
            log_user(f"Export complete: {msg}", bold_parts=[msg])
            self.show_status(msg)
            box = QMessageBox(QMessageBox.Information, "Export Complete", msg, parent=self)
            self.show_message_box(box)
        else:
            log_user(f"Error: {msg}", bold_parts=[msg])
            self.show_status("Export failed.")
            box = QMessageBox(QMessageBox.Critical, "Export Error", msg, parent=self)
            self.show_message_box(box)

    def stop_export(self):
        if hasattr(self, 'export_thread') and self.export_thread.isRunning():
            self.export_thread.terminate()
            self.export_thread.wait()
            self.show_status("Export stopped by user.")
            self.logTextEdit.append("Export stopped by user.")
            self.set_controls_enabled(True)
            self.set_shortcuts_enabled(True)
            self.stopExportBtn.setEnabled(False)
            self.stopExportBtn.setVisible(False)
            self.progressBar.setVisible(False)

    def show_status(self, msg):
        self.statusBar.showMessage(msg)

    def update_slider_highlight(self):
        pos = self.vlc_player.get_time()
        for seg in self.segments:
            if seg.start <= pos <= seg.end:
                self.slider.setToolTip(f"In segment: {seg}")
                return
        self.slider.setToolTip("")

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.output_folder.setText(self.settings['output_folder'])
        dlg.filename_pattern.setText(self.settings['filename_pattern'])
        dlg.reencode.setChecked(self.settings['reencode'])
        if dlg.exec_():
            self.settings['output_folder'] = dlg.output_folder.text()
            self.settings['filename_pattern'] = dlg.filename_pattern.text()
            self.settings['reencode'] = dlg.reencode.isChecked()

    def open_about(self):
        dlg = AboutDialog(self)
        dlg.exec_()

    def show_message_box(self, box):
        box.setMinimumWidth(400)
        return box.exec_()

def main():
    app = QApplication(sys.argv)
    window = SlyceApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
