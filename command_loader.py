"""
command_loader.py

用途：
- 讀取並解析 Command.txt 檔案，格式：「名稱 = 指令」
- 忽略空行與 # 註解
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class CommandItem:
    name: str
    command: str


def load_commands_from_file(path: Path) -> List[CommandItem]:
    if not path.exists():
        raise FileNotFoundError(f'找不到指令檔案：{path}')

    items: List[CommandItem] = []
    with path.open('r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            name, cmd = line.split('=', 1)
            name = name.strip()
            cmd = cmd.strip()
            if name and cmd:
                items.append(CommandItem(name=name, command=cmd))
    return items


