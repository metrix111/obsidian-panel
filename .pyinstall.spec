# -*- mode: python -*-

block_cipher = None


a = Analysis(['launch.py'],
             pathex=['./env/lib/python3.5/site-packages', './ftp_manager', './process_watcher', './task_scheduler', './websocket_server', './app'],
             binaries=[],
             datas=[('VERSION', '.'),('config.yaml.sample', '.')],
             hiddenimports=['tornado', 'yaml', 'pyftpdlib', 'distro', 'zmq', 'zmq.backend.cython'],
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
