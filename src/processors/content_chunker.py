# src/processors/content_chunker.py
from typing import List, Dict, Any
from ..models.invoice_models import DocumentStructure, InvoiceSection

class ContentChunker:
    def __init__(self, max_chunk_size: int = 2000):
        self.max_chunk_size = max_chunk_size
    
    def chunk_by_structure(self, structure: DocumentStructure, raw_markdown: str) -> List[Dict[str, Any]]:
        """Chunk content based on document structure"""
        chunks = []
        
        for section in structure.sections:
            section_chunks = self._chunk_section(section, raw_markdown)
            chunks.extend(section_chunks)
        
        return chunks
    
    def _chunk_section(self, section: InvoiceSection, raw_markdown: str) -> List[Dict[str, Any]]:
        """Chunk a single section maintaining context"""
        chunks = []
        
        # If section is small enough, keep as single chunk
        if len(section.content) <= self.max_chunk_size:
            chunks.append({
                'section_title': section.title,
                'section_level': section.level,
                'content': section.content,
                'chunk_index': 0,
                'total_chunks': 1,
                'context': self._build_context(section)
            })
        else:
            # Split large sections into smaller chunks
            content_chunks = self._split_content_intelligently(section.content)
            
            for i, chunk_content in enumerate(content_chunks):
                chunks.append({
                    'section_title': section.title,
                    'section_level': section.level,
                    'content': chunk_content,
                    'chunk_index': i,
                    'total_chunks': len(content_chunks),
                    'context': self._build_context(section)
                })
        
        return chunks
    
    def _split_content_intelligently(self, content: str) -> List[str]:
        """Split content at natural boundaries"""
        # Try to split at paragraph boundaries first
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk + paragraph) <= self.max_chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _build_context(self, section: InvoiceSection) -> str:
        """Build context information for the section"""
        context = f"Section: {section.title} (Level {section.level})"
        
        # Add parent context if available
        if hasattr(section, 'parent_title'):
            context += f" | Parent: {section.parent_title}"
        
        return context
