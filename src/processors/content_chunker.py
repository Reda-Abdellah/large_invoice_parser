# src/processors/content_chunker.py
from typing import List, Dict, Any

class ContentChunker:
    def __init__(self, max_chunk_size: int = 2000, context_window_size: int = 8192):
        self.max_chunk_size = max_chunk_size
        self.context_window_size = context_window_size  
    
    def chunk_by_structure(self, structure: Dict[str, Any], raw_markdown: str) -> List[Dict[str, Any]]:
        """Chunk content based on document structure and context window size"""
        chunks = []
        
        # Extract sections from the enhanced structure
        sections = structure.get('sections', [])
        
        for section_data in sections:
            section_chunks = self._chunk_section_from_data(section_data, raw_markdown)
            chunks.extend(section_chunks)
        
        return chunks

    def _chunk_section_from_data(self, section_data: Dict[str, Any], raw_markdown: str) -> List[Dict[str, Any]]:
        """Chunk a section from structure data"""
        chunks = []
        content = section_data.get('content', '')
        
        # Estimate tokens for the section
        try:
            estimated_tokens = self.ollama_client.estimate_tokens(content)
            if not isinstance(estimated_tokens, int):
                estimated_tokens = int(estimated_tokens) if estimated_tokens else 1
        except Exception as e:
            estimated_tokens = max(1, len(content.split()))
            print(f"Warning: Token estimation failed for section '{section_data['title']}': {e}")
        
        # Calculate available space
        available_context = self.context_window_size - 1000
        
        if estimated_tokens <= available_context:
            # Section fits in single chunk
            chunks.append({
                'section_title': section_data['title'],
                'section_level': section_data['level'],
                'content': content,
                'content_type': section_data.get('content_type', 'general'),
                'estimated_items': section_data.get('estimated_items', 0),
                'chunk_index': 0,
                'total_chunks': 1,
                'estimated_tokens': estimated_tokens,
                'context': self._build_context_from_data(section_data)
            })
        else:
            # Split section into multiple chunks
            print(f"Section '{section_data['title']}' ({estimated_tokens} tokens) "
                f"exceeds context window. Splitting into chunks...")
            
            content_chunks = self._split_content_by_tokens(content, available_context)
            
            for i, chunk_content in enumerate(content_chunks):
                try:
                    chunk_tokens = self.ollama_client.estimate_tokens(chunk_content)
                    if not isinstance(chunk_tokens, int):
                        chunk_tokens = int(chunk_tokens) if chunk_tokens else 1
                except Exception as e:
                    chunk_tokens = max(1, len(chunk_content.split()))
                    print(f"Warning: Token estimation failed for chunk {i}: {e}")
                
                chunks.append({
                    'section_title': section_data['title'],
                    'section_level': section_data['level'],
                    'content': chunk_content,
                    'content_type': section_data.get('content_type', 'general'),
                    'estimated_items': section_data.get('estimated_items', 0) // len(content_chunks),
                    'chunk_index': i,
                    'total_chunks': len(content_chunks),
                    'estimated_tokens': chunk_tokens,
                    'context': self._build_context_from_data(section_data, f"Part {i+1}/{len(content_chunks)}")
                })
        
        return chunks

    def _build_context_from_data(self, section_data: Dict[str, Any], chunk_info: str = "") -> str:
        """Build context information from section data"""
        context = f"Section: {section_data['title']} (Level {section_data['level']})"
        context += f" | Type: {section_data.get('content_type', 'general')}"
        
        if chunk_info:
            context += f" | {chunk_info}"
        
        return context