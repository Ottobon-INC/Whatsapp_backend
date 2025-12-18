# modules/text_utils.py
"""
Utility functions for text processing.
"""

MAX_RESPONSE_LENGTH = 1024


def truncate_response(text: str, max_length: int = MAX_RESPONSE_LENGTH) -> str:
    """
    Truncate text to a maximum character length.
    
    Args:
        text: The text to truncate
        max_length: Maximum allowed length (default: 1024)
    
    Returns:
        Truncated text that fits within max_length
    """
    if not text:
        return text
    
    # If text is already within limit, return as is
    if len(text) <= max_length:
        return text
    
    # Truncate to max_length - 3 to add ellipsis
    truncated = text[:max_length - 3].rstrip()
    
    # Try to truncate at a sentence boundary for better readability
    # Look for the last sentence ending punctuation
    last_period = truncated.rfind('.')
    last_exclamation = truncated.rfind('!')
    last_question = truncated.rfind('?')
    last_newline = truncated.rfind('\n')
    
    # Find the latest sentence boundary
    sentence_end = max(last_period, last_exclamation, last_question, last_newline)
    
    # If we found a sentence boundary within reasonable distance (not too far back)
    # use it, otherwise just use the hard truncation
    if sentence_end > max_length * 0.7:  # Within last 30% of text
        truncated = truncated[:sentence_end + 1]
    else:
        # Add ellipsis to indicate truncation
        truncated += "..."
    
    return truncated
