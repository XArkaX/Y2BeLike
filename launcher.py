#!/usr/bin/env python3
"""
Launcher script to run YouTube Downloader without console window on Windows
"""
import sys
import os
import subprocess

if __name__ == "__main__":
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    download_script = os.path.join(script_dir, 'download.py')

    # Check if we're on Windows
    if os.name == 'nt':
        # Use pythonw.exe to run without console window
        pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
        if os.path.exists(pythonw):
            subprocess.run([pythonw, download_script])
        else:
            # Fallback to regular python if pythonw not found
            subprocess.run([sys.executable, download_script])
    else:
        # On other platforms, run normally
        subprocess.run([sys.executable, download_script])