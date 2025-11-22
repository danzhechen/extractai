"""Entry point for running pdf_reader as a module.

Allows running: python -m pdf_reader extract --input file.pdf
"""

from .cli import main

if __name__ == "__main__":
    import sys

    sys.exit(main())



