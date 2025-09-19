#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_version_info.py - 產生 PyInstaller 可用的 version_info.txt

從 settings.json 讀取 app.version（例如 v1.2.3），預設 v1.2.0。
輸出 version_info.txt（ASCII），供 --version-file 使用。
"""

import json
from pathlib import Path


def read_version() -> str:
    try:
        cfg_path = Path('settings.json')
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text('utf-8'))
            v = (
                data.get('app', {}).get('version')
                or data.get('connection', {}).get('version')
            )
            if isinstance(v, str) and v.strip():
                return v.strip()
    except Exception:
        pass
    return 'v1.2.0'


def main() -> int:
    v = read_version()
    ver = v.lstrip('vV') or '1.2.0'
    parts = (ver.split('.') + ['0', '0', '0'])[:4]
    try:
        maj, min_, build = int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        maj, min_, build = 1, 2, 0
    patch = 0

    tmpl = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({maj}, {min_}, {build}, {patch}),
    prodvers=({maj}, {min_}, {build}, {patch}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '4CAM DEBUG TOOL'),
        StringStruct('FileDescription', '4CAM DEBUG TOOL'),
        StringStruct('FileVersion', '{v}'),
        StringStruct('InternalName', '4CAM_DEBUG_TOOL'),
        StringStruct('LegalCopyright', '(C) 2025'),
        StringStruct('OriginalFilename', '4CAM_DEBUG_TOOL.exe'),
        StringStruct('ProductName', '4CAM DEBUG TOOL'),
        StringStruct('ProductVersion', '{v}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""".strip()

    Path('version_info.txt').write_text(tmpl, encoding='ascii')
    print(f'Version info generated: {v}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


