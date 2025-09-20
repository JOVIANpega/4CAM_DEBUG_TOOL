#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_icon.py - 產生專案圖示（ICO）

用途：
- 產生綠色背景、白色文字「4cam」的圖示
- 尺寸輸出：16, 32, 48（ICO 多尺寸）
- 儲存到 assets/icon.ico

作者：AI 助手
版本：1.1.0
"""

from PIL import Image, ImageDraw, ImageFont
import os

def _load_font(preferred_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """嘗試載入系統較常見字體，失敗則使用內建位圖字體。"""
    font_candidates = [
        ("C:/Windows/Fonts/arialbd.ttf", preferred_size),
        ("C:/Windows/Fonts/msjhbd.ttc", preferred_size),  # 微軟正黑體-粗體
        ("C:/Windows/Fonts/msyhbd.ttc", preferred_size),  # 微軟雅黑-粗體
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", preferred_size),
    ]
    for path, size in font_candidates:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_simple_icon():
    """創建綠底 4cam 文字的圖示檔案"""
    try:
        # 確保 assets 資料夾存在
        os.makedirs('assets', exist_ok=True)
        
        base_size = 256  # 放大基底尺寸，輸出高解析度圖示
        bg_color = (28, 158, 88)  # 綠色
        fg_color = (255, 255, 255)  # 白色

        canvas = Image.new('RGBA', (base_size, base_size), bg_color)
        draw = ImageDraw.Draw(canvas)

        # 畫圓角矩形加點陰影（簡單效果）
        try:
            radius = max(12, base_size // 16)
            draw.rounded_rectangle([2, 2, base_size - 3, base_size - 3], radius=radius, outline=(0, 0, 0, 60), width=max(2, base_size // 128))
        except Exception:
            pass

        # 置中寫 4cam 文案
        font = _load_font(preferred_size=max(34, base_size // 2))
        text = "Cam"
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except Exception:
            # 回退估算
            w, h = (base_size // 2, base_size // 3)
        x = (base_size - w) // 2
        y = (base_size - h) // 2 - 1
        # 簡單描邊
        outline = max(1, base_size // 128)
        for dx, dy in [(-outline, 0), (outline, 0), (0, -outline), (0, outline)]:
            draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 90))
        draw.text((x, y), text, font=font, fill=fg_color)

        # 輸出 ICO 多尺寸
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        images = [canvas.resize(sz, Image.Resampling.LANCZOS) for sz in icon_sizes]
        images[0].save('assets/icon.ico', format='ICO', sizes=icon_sizes)
        
        print("圖示檔案已成功創建：assets/icon.ico")
        return True
        
    except ImportError:
        print("錯誤：需要安裝 Pillow 庫")
        print("請執行：pip install Pillow")
        return False
    except Exception as e:
        print(f"創建圖示時發生錯誤：{e}")
        return False

if __name__ == "__main__":
    create_simple_icon()
