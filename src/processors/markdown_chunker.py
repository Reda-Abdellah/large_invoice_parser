# src/processors/markdown_chunker.py
from typing import List, Dict, Any
import hashlib

class MarkdownChunker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.chunk_size = config.get('chunk_size', 4000)  # Characters per chunk
        self.overlap_size = config.get('overlap_size', 400)  # Overlap between chunks
        self.context_window_size = config.get('context_window_size', 8192)
        
    
    def create_overlapping_chunks(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Create overlapping chunks from markdown content"""
        chunks = []
        content_length = len(markdown_content)
        
        if content_length <= self.chunk_size:
            # Single chunk if content is small
            chunks.append({
                'chunk_id': self._generate_chunk_id(markdown_content, 0),
                'chunk_index': 0,
                'total_chunks': 1,
                'content': markdown_content,
                'start_char': 0,
                'end_char': content_length,
                'estimated_tokens': estimate_tokens(markdown_content),
                'overlap_with_previous': False,
                'overlap_with_next': False
            })
            return chunks
        
        start = 0
        chunk_index = 0
        
        while start < content_length:
            # Calculate end position
            end = min(start + self.chunk_size, content_length)
            
            # Try to break at natural boundaries (paragraphs, then sentences)
            if end < content_length:
                end = self._find_natural_break(markdown_content, start, end)
            
            chunk_content = markdown_content[start:end]
            print(f'chunk delimeter start: {start}, end: {end}.')  # Debug output
            chunks.append({
                'chunk_id': self._generate_chunk_id(chunk_content, chunk_index),
                'chunk_index': chunk_index,
                'total_chunks': 0,  # Will be updated after all chunks are created
                'content': chunk_content,
                'start_char': start,
                'end_char': end,
                'estimated_tokens': estimate_tokens(chunk_content),
                'overlap_with_previous': chunk_index > 0,
                'overlap_with_next': end < content_length
            })
            
            # Move start position with overlap
            if end >= content_length:
                break
            
            start = end - self.overlap_size
            chunk_index += 1
        
        # Update total_chunks for all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk['total_chunks'] = total_chunks
        
        print(f"Created {total_chunks} overlapping chunks from {content_length} characters")
        return chunks
    
    def _find_natural_break(self, content: str, start: int, preferred_end: int, window: int= 150) -> int:
        """Find natural break point near preferred end"""
        # Look for paragraph breaks first
        search_start = max(start, preferred_end - window)
        search_end = min(len(content), preferred_end + window)
        
        # Look for double newlines (paragraph breaks)
        for i in range(search_end, search_start, -1):
            if i < len(content) - 1 and content[i:i+2] == '\n\n':
                return i + 2
        
        # Look for single newlines
        for i in range(search_end, search_start, -1):
            if content[i] == '\n':
                return i + 1
        
        # Look for sentence endings
        for i in range(search_end, search_start, -1):
            if content[i] in '.!?':
                return i + 1
        
        # Fallback to preferred end
        return preferred_end
    
    def _generate_chunk_id(self, content: str, index: int) -> str:
        """Generate unique chunk ID"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"chunk_{index}_{content_hash}"




def estimate_tokens(text: str) -> int:
    """Rough estimation of token count (1 token ≈ 0.75 words)"""
    word_count = len(text.split())
    return int(word_count / 0.75)

def check_context_requirements(text: str, 
                                context_size: int) -> Dict[str, Any]:
    """Check if text fits within context window"""
    estimated_tokens = estimate_tokens(text)
    # print(estimated_tokens <= context_size)
    return {
        "estimated_tokens": estimated_tokens,
        "context_size": context_size,
        "fits_in_context": estimated_tokens <= context_size,
        "utilization_percentage": (estimated_tokens / context_size) * 100
    }
