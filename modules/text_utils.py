# modules/text_utils.py
"""
Utility functions for text processing.
"""

import tiktoken

MAX_RESPONSE_LENGTH = 1024  # WhatsApp-friendly character limit


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Count the number of tokens in a text string.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


def truncate_by_tokens(text: str, max_tokens: int, model: str = "gpt-4o") -> str:
    """
    Truncate text to a maximum token count.
    """
    if not text:
        return text
        
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
        
    tokens = encoding.encode(text)
    
    # If already within limit
    if len(tokens) <= max_tokens:
        return text
        
    # Truncate tokens and decode back to string
    truncated_tokens = tokens[:max_tokens]
    truncated_text = encoding.decode(truncated_tokens)
    
    return truncated_text



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
    
    
    # Post-process for WhatsApp formatting
    text = clean_whatsapp_formatting(text)
    
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

def clean_whatsapp_formatting(text: str) -> str:
    """
    Ensure formatting is compatible with WhatsApp.
    1. Convert Asterisk Bullets (* Item) to Hyphen Bullets (- Item).
    2. Convert Markdown bold (**text**) to WhatsApp bold (*text*).
    3. Convert Markdown headers (### Header) to Bold (*Header*).
    """
    import re
    
    # 1. Convert Star Bullets (* Item) to Hyphen Bullets (- Item)
    # Matches start of line, optional whitespace, asterisk, ONE OR MORE spaces
    text = re.sub(r'^\s*\*\s+', '- ', text, flags=re.MULTILINE)
    
    # 2. Convert **bold** to *bold*
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    
    # 3. Convert ### Header to *Header*
    text = re.sub(r'#+\s*(.*?)\n', r'*\1*\n', text)
    
    return text
