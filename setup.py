"""Setup script for pdf-reading-project."""

from setuptools import setup, find_packages

setup(
    name="pdf-reader",
    version="0.1.0",
    description="PDF table extraction with position verification",
    author="PDF Reader Team",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "pdfplumber>=0.11.0",
        "pillow>=10.0.0",
        "numpy>=1.24.0,<2.0.0",
        "opencv-python>=4.8.0",
        "pydantic>=2.5.0",
        "rich>=13.0.0",
        "reportlab>=3.6.0",
        "pyyaml>=6.0.0",
        "google-generativeai>=0.3.0",
        "openai>=1.0.0",
        "openpyxl>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "pdf-reader=pdf_reader.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

