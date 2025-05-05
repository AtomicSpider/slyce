# Slyce

![Build](https://github.com/AtomicSpider/slyce/actions/workflows/build-app.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/AtomicSpider/slyce)
![GitHub all releases](https://img.shields.io/github/downloads/AtomicSpider/slyce/total)
![Platform](https://img.shields.io/badge/platform-windows-blue)
![GitHub issues](https://img.shields.io/github/issues/AtomicSpider/slyce)

Slyce is a Python desktop app for quickly marking and losslessly slicing multiple video segments from a single video file. Built with Python, PyQt5, and VLC/FFmpeg.

![Demo GIF](extras/slyce-demo.gif)

## Features
- Fast, lossless video segmenting
- Multi-segment export
- Modern PyQt5 GUI
- Uses FFmpeg and VLC for robust media support

## Installation

1. **Clone this repository:**
   ```sh
   git clone https://github.com/AtomicSpider/slyce.git
   cd slyce
   ```
2. **Install [Git LFS](https://git-lfs.github.com/) and pull binaries:**
   ```sh
   git lfs install
   git lfs pull
   ```
3. **Install Python 3.11 (or 3.8+) and dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

## Usage

- **Development mode:**
  ```sh
  python slyce.py
  ```
- **Build a Windows EXE:**
  ```sh
  pyinstaller slyce.spec
  # The EXE and all dependencies will be in dist/slyce.exe
  ```
- **Run the built EXE:**
  Double-click `dist/slyce.exe` or run from command line.

## How to Use Slyce

1. **Load a Video:**
   - Click the "Load Videos" button and select a folder containing your video files, or drag and drop video files into the playlist panel on the left.
   - Double-click a video in the playlist to load it.

2. **Mark Segments:**
   - Use the Play/Pause and seek bar to navigate the video.
   - Click **Start (S)** at the desired segment start time.
   - Click **End (E)** at the desired segment end time.
   - The segment will appear in the Segments list. Repeat to add more segments.
   - Use **Undo (Ctrl+Z)** and **Redo (Ctrl+Y)** to manage segments.

3. **Export Segments:**
   - Click **Export (Ctrl+E)** to save all marked segments as separate video files in the same folder as the source video.
   - Progress is shown in the status bar and log panel.

4. **Other Controls:**
   - **Mute (M):** Toggle audio mute.
   - **Stop Export:** Cancel an ongoing export.
   - **Settings:** Configure output folder, filename pattern, and re-encoding options.
   - **About:** View app info.

5. **Keyboard Shortcuts:**
   - Space: Play/Pause
   - S: Mark Start
   - E: Mark End
   - Ctrl+E: Export
   - Ctrl+Z: Undo
   - Ctrl+Y: Redo
   - M: Mute

## Binaries
- FFmpeg and VLC DLLs are included via Git LFS in the `bin/` directory.
- If you clone without LFS, download FFmpeg and VLC manually and place them in `bin/`.
- VLC plugins are required in `bin/vlc/plugins/`.

## Contributing
Pull requests are welcome! Please open an issue first to discuss major changes.

## License
This project is licensed under the [CC BY-NC 4.0 License](https://creativecommons.org/licenses/by-nc/4.0/).

## Acknowledgements
- [PyQt5](https://riverbankcomputing.com/software/pyqt/intro/)
- [python-vlc](https://pypi.org/project/python-vlc/)
- [FFmpeg](https://ffmpeg.org/)
- [VLC](https://www.videolan.org/vlc/)

