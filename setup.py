#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4CAM_DEBUG_TOOL 安裝設定檔
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="4cam-debug-tool",
    version="1.2.0",
    author="AI Assistant",
    author_email="",
    description="4攝影機 DUT SSH 控制工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JOVIANpega/4CAM_DEBUG_TOOL",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "4cam-debug-tool=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.html", "*.ico"],
    },
)
