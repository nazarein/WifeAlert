# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import certifi
import desktop_notifier

# Add the project root directory to the path
project_root = os.path.abspath(SPECPATH)
sys.path.insert(0, project_root)

# Get certifi certificate path
cert_path = certifi.where()

# Get desktop_notifier resources path
desktop_notifier_path = os.path.dirname(desktop_notifier.__file__)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('assets/*', 'assets/'),
        ('config.py', '.'),
        (cert_path, '.'),  # Include SSL certificates
        (os.path.join(desktop_notifier_path, 'resources'), 'desktop_notifier/resources'),  # Include desktop-notifier resources
    ],
    hiddenimports=[
        # Qt dependencies
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimedia.QSoundEffect',
        'PyQt6.QtMultimedia.QMediaDevices',
        
        # Windows specific
        'win32gui',
        'win32process',
        'win32security',
        'win32api',
        'win32con',
        'win32com',
        'ntsecuritycon',
        'win32com.shell',
        
        # Networking and async
        'websockets.legacy.client',
        'websockets.legacy.server',
        'websockets.legacy.protocol',
        'aiohttp',
        'asyncio',
        'socket',
        'certifi',
        'ssl',
        
        # Notifications
        'desktop_notifier',
        
        # Cryptography
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        
        # Other utilities
        'json',
        'base64',
        'hashlib',
        'secrets',
        'webbrowser',
        'qasync',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    collect_submodules=['desktop_notifier'],  # Ensure all desktop_notifier modules are included
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WifeAlert',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    environ={
        'QT_LOGGING_RULES': 'qt.multimedia.ffmpeg.*=false'  # Suppress FFmpeg init messages
    },
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico'
)
