#
# 
#

import pathlib
import requests


class CsvFetchError(Exception):
    """Base exception for errors while fetching CSV data."""
    pass


class FileReadError(CsvFetchError):
    """Raised for errors related to reading a local CSV file."""
    pass


class UrlReadError(CsvFetchError):
    """Raised for errors related to fetching a CSV from a URL."""
    pass


def readCsvFile(path: pathlib.Path) -> str:
    """
    Reads CSV text from the specified file.

    Args:
        `path`: A `pathlib.Path` object pointing to the source file.

    Returns:
        The text content of the file as a string.

    Raises:
        `FileReadError`: Specifies why reading the file failed.
    """
    try:
        # Using utf-8 is a safe default for text-based data like CSV.
        return path.read_text(encoding='utf-8')
    except (FileNotFoundError, PermissionError, UnicodeDecodeError, OSError
            ) as e:
        # Wrap the original exception to provide more context.
        raise FileReadError(f"Failed to read file at '{path}': {e}") from e


def readCsvUrl(url: str, timeout: int = 20) -> str:
    """
    Reads CSV text from the specified URL.

    Args:
        `url`: The URL of the text resource.
        `timeout`: The number of seconds to wait for a server response.

    Returns:
        The text content of the resource as a string.

    Raises:
        `UrlReadError`: Wraps network-related exceptions specifying the 
            reason of failure (e.g., connection errors, timeouts, bad
            status codes).
    """
    try:
        response = requests.get(url, timeout=timeout)
        # This will raise an HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()
        # The vpngate.net API returns text, so we access it directly
        return response.text
    except requests.exceptions.RequestException as e:
        # Wrap the original exception to provide more context.
        raise UrlReadError(
            f"Failed to fetch data from URL '{url}': {e}") from e
