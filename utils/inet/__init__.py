"""
This module provides utilities for working with internet resources.
"""


import requests


def fetchTextRes(url: str, timeout: float = 10.0) -> str:
    """
    Fetches a text resource from a URL, checks that it's plain text, and
    decodes it using the character set specified in the Content-Type
    header. Raises exceptions for network errors, server errors, and MIME
    type errors.

    Args:
        url: The URL to fetch the resource from.
        timeout: Maximum time to wait for the server response in seconds
            (default: 10.0).

    Returns:
        The decoded text content of the response.

    Raises:
        ValueError: If the Content-Type is not 'text/plain' or is missing.
        requests.HTTPError: For HTTP 4xx or 5xx status codes (e.g., 403, 503).
        requests.exceptions.RequestException: Something wrong happened with
            the network, URL, etc. such as:
            requests.exceptions.ConnectionError
        requests.Timeout: If the request times out.
        requests.ConnectionError: For network issues like DNS failure.
        requests.RequestException: For other request-related errors.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get('Content-Type', '').lower()
    media_type = content_type.split(';', 1)[0].strip()
    if media_type != 'text/plain':
        raise ValueError(f"Expected 'text/plain', but got '{media_type}'")
    # Decoding & returning the text...
    return response.text