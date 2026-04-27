"""Requirements Extractor — pull structured requirements out of .docx specs."""

from .extractor import extract_from_files, ExtractionResult

__all__ = ["extract_from_files", "ExtractionResult"]
__version__ = "0.6.0"
