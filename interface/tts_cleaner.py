import re

def clean_text_for_tts(text: str) -> str:
    """
    Sanitize text for human-like speech synthesis.
    
    Removes:
    - Emojis
    - Markdown (bold, italic markers)
    - URLs
    - Excess whitespace
    
    Args:
        text: Raw text from AI
        
    Returns:
        Cleaned text ready for TTS
    """
    if not text:
        return ""
        
    # 1. Remove Emojis (Range approximation for performance)
    # Removing common emoji ranges
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    
    # 2. Remove Markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)     # Italic
    text = re.sub(r'`(.*?)`', r'\1', text)       # Code inline
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text) # Links: [text](url) -> text
    
    # 3. Remove artifacts like "http://..."
    text = re.sub(r'http\S+', '', text)
    
    # 4. Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

if __name__ == "__main__":
    # Test
    sample = "Hello! 🦉 This is **bold** and this is a link [Google](http://google.com). Peace! ✨"
    print(f"Original: {sample}")
    print(f"Cleaned:  {clean_text_for_tts(sample)}")
