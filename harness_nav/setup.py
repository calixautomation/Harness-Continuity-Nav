#!/usr/bin/env python3
"""Setup script for Harness Navigation System."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="harness-nav",
    version="1.0.0",
    description="GUI-controlled harness navigation system for wire connectivity testing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/harness-nav",
    license="MIT",
    python_requires=">=3.8",

    packages=find_packages(exclude=["tests", "tests.*"]),

    include_package_data=True,
    package_data={
        "harness_nav": [
            "config/*.yaml",
            "data/*.csv",
            "gui/resources/*.qss",
            "gui/resources/icons/*",
        ],
    },

    install_requires=[
        "PyQt5>=5.15.0",
        "PyYAML>=6.0",
    ],

    extras_require={
        "beaglebone": [
            "Adafruit-BBIO>=1.2.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.0.0",
            "pytest-cov>=4.0.0",
            "mypy>=1.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
        ],
    },

    entry_points={
        "console_scripts": [
            "harness-nav=harness_nav.main:main",
        ],
    },

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Manufacturing",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],

    keywords="harness, wire, testing, beaglebone, led-matrix, pyqt5",
)
