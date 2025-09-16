#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_icon.py - 創建簡單的 ICO 圖示檔案

主要用途：
- 為 4CAM_DEBUG_TOOL 創建一個簡單的 ICO 圖示檔案
- 使用 Pillow 庫生成 32x32 和 16x16 的圖示
- 儲存到 assets/icon.ico

作者：AI 助手
版本：1.0.0
"""

from PIL import Image, ImageDraw
import os

def create_simple_icon():
    """創建簡單的圖示檔案"""
    try:
        # 確保 assets 資料夾存在
        os.makedirs('assets', exist_ok=True)
        
        # 創建 32x32 的圖示
        size = 32
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 繪製一個簡單的相機圖示
        # 外框
        draw.rectangle([4, 8, 28, 24], fill=(70, 130, 180), outline=(0, 0, 0), width=2)
        
        # 鏡頭
        draw.ellipse([10, 12, 22, 20], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
        
        # 鏡頭中心
        draw.ellipse([13, 15, 19, 17], fill=(0, 0, 0))
        
        # 閃光燈
        draw.rectangle([20, 6, 24, 8], fill=(255, 255, 0))
        
        # 儲存為 ICO 格式（包含多種尺寸）
        icon_sizes = [(16, 16), (32, 32), (48, 48)]
        images = []
        
        for icon_size in icon_sizes:
            resized_img = img.resize(icon_size, Image.Resampling.LANCZOS)
            images.append(resized_img)
        
        # 儲存 ICO 檔案
        images[0].save('assets/icon.ico', format='ICO', sizes=[(img.width, img.height) for img in images])
        
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
