import os
import re
import logging
import colorlog
import argparse
import sys
import mimetypes
from pathlib import Path

# Configure logging
def setup_logging(log_level, log_to_file=None):
    handler_list = []

    # Console handler with color
    console_handler = colorlog.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    handler_list.append(console_handler)

    # File handler without color
    if log_to_file:
        file_handler = logging.FileHandler(log_to_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        handler_list.append(file_handler)

    logger = colorlog.getLogger()
    for handler in handler_list:
        logger.addHandler(handler)
    logger.setLevel(log_level)

    return logger

def detect_language_and_directory(file_name, custom_patterns=None):
    """
    Detect file type and suggest directory structure based on the file's extension.
    Supports custom patterns.
    """
    # Default patterns
    patterns = {
        "python": (["backend"], r"\.py$"),
        "javascript": (["frontend"], r"\.js$"),
        "jsx": (["frontend"], r"\.jsx$"),
        "html": (["templates"], r"\.html$"),
        "css": (["static", "css"], r"\.css$"),
        "json": (["static", "data"], r"\.json$"),
        "yaml": (["config"], r"\.(yaml|yml)$"),
        "markdown": (["docs"], r"\.md$"),
        # Add more default patterns as needed
    }

    # Update with custom patterns if provided
    if custom_patterns:
        patterns.update(custom_patterns)

    for language, (directory, pattern) in patterns.items():
        if re.search(pattern, file_name, re.IGNORECASE):
            logger.debug(f"Detected file type '{language}' for file: {file_name}")
            return language, directory

    # Use mimetypes as a fallback
    mime_type, _ = mimetypes.guess_type(file_name)
    if mime_type:
        main_type = mime_type.split('/')[0]
        directory = [main_type]
        logger.debug(f"Using mimetypes: Detected MIME type '{mime_type}' for file: {file_name}")
        return mime_type, directory

    logger.warning(f"Could not detect file type for file: {file_name}. Defaulting to 'misc'.")
    return "txt", ["misc"]

def save_file(file_name, directory, file_content, output_dir):
    """
    Save the detected file into its proper directory structure.
    """
    try:
        # Ensure the directory exists
        target_dir = Path(output_dir).joinpath(*directory)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Save the file
        file_path = target_dir / file_name
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content.strip())

        logger.info(f"Saved: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save {file_name}: {e}")

def extract_full_files(file_path, output_dir, custom_patterns=None):
    """
    Extract full files from a markdown file and save them to a structured directory.
    """
    logger.info(f"Processing file: {file_path}")
    
    if not os.path.isfile(file_path):
        logger.error(f"Input file does not exist: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        return

    # Regex to detect file blocks
    # Supports optional language specifier after the filename
    file_pattern = re.compile(
        r"^#\s*(\S+\.(py|js|jsx|html|css|json|yaml|yml|md))\s*\n(?:```(\w+)?\n)?([\s\S]*?)(?:```|(?=^# |\Z))",
        re.MULTILINE
    )

    matches = file_pattern.findall(content)
    if not matches:
        logger.error("No files found in the markdown.")
        return

    logger.info(f"Found {len(matches)} file(s) in the markdown.")

    for match in matches:
        file_name = match[0].strip()
        extension = match[1].strip()
        language_specifier = match[2].strip() if match[2] else ''
        file_content = match[3].strip()

        logger.debug(f"Extracting file: {file_name} (Language specifier: {language_specifier})")

        # Determine directory based on file extension
        language, directory = detect_language_and_directory(file_name, custom_patterns)

        # Save the file
        save_file(file_name, directory, file_content, output_dir)

    logger.info("All files have been processed and saved.")

def parse_arguments():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Extract and organize files embedded within a Markdown document."
    )
    parser.add_argument(
        'input_file',
        type=str,
        help='Path to the input Markdown file containing embedded files.'
    )
    parser.add_argument(
        'output_directory',
        type=str,
        help='Directory where the extracted files will be saved.'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level (default: INFO).'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Optional path to a log file.'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Optional path to a configuration file for custom patterns (e.g., JSON).'
    )
    return parser.parse_args()

def load_custom_patterns(config_path):
    """
    Load custom patterns from a JSON configuration file.
    Expected format:
    {
        "language_name": ["directory", "regex_pattern"],
        ...
    }
    """
    import json

    if not os.path.isfile(config_path):
        logger.error(f"Configuration file does not exist: {config_path}")
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            patterns = json.load(f)
        # Ensure the patterns are in the correct format
        for lang, (dir_path, pattern) in patterns.items():
            if not isinstance(dir_path, list) or not isinstance(pattern, str):
                logger.warning(f"Invalid pattern for '{lang}'. Skipping.")
                del patterns[lang]
        logger.info(f"Loaded custom patterns from {config_path}")
        return patterns
    except Exception as e:
        logger.error(f"Failed to load custom patterns: {e}")
        return {}

if __name__ == "__main__":
    args = parse_arguments()
    logger = setup_logging(args.log_level, args.log_file)

    custom_patterns = {}
    if args.config:
        custom_patterns = load_custom_patterns(args.config)

    extract_full_files(args.input_file, args.output_directory, custom_patterns)
    logger.info("Extraction process completed.")
