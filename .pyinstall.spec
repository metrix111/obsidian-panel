# -*- mode: python -*-

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT, BUNDLE, TOC

block_cipher = None

a = Analysis(['launch.py'],
             pathex=['./env/lib/python3.5/site-packages','./env/lib/python3.5/site-packages/zmq','./env/lib/python3.5/site-packages/APScheduler', './env/Lib/site-packages','./env/Lib/site-packages/zmq','./env/Lib/site-packages/APScheduler', './ftp_manager', './process_watcher', './task_scheduler', './websocket_server', './app'],
             binaries=[],
             datas=[('VERSION', '.'),('config.yaml.sample', '.')],
             hiddenimports=['tornado', 'yaml', 'pyftpdlib', 'distro', 'zmq'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='obsidian-panel',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='launch')
