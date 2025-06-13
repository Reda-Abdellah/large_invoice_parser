# src/pipeline/invoice_pipeline.py
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from ..models.pipeline_state import PipelineState
from ..processors.structure_extractor import StructureExtractor
from ..processors.content_chunker import ContentChunker
from ..processors.section_analyzer import SectionAnalyzer
from ..processors.json_merger import JsonMerger

class InvoicePipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.structure_extractor = StructureExtractor(config.get('structure_model', 'llama3.2:3b'))
        self.content_chunker = ContentChunker(config.get('max_chunk_size', 2000))
        self.section_analyzer = SectionAnalyzer(config.get('analysis_model', 'llama3.2:7b'))
        self.json_merger = JsonMerger()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph pipeline"""
        workflow = StateGraph(PipelineState)
        
        # Add nodes
        workflow.add_node("extract_structure", self._extract_structure_node)
        workflow.add_node("chunk_content", self._chunk_content_node)
        workflow.add_node("analyze_sections", self._analyze_sections_node)
        workflow.add_node("merge_json", self._merge_json_node)
        
        # Add edges
        workflow.set_entry_point("extract_structure")
        workflow.add_edge("extract_structure", "chunk_content")
        workflow.add_edge("chunk_content", "analyze_sections")
        workflow.add_edge("analyze_sections", "merge_json")
        workflow.add_edge("merge_json", END)
        
        return workflow.compile()
    
    def _extract_structure_node(self, state: PipelineState) -> PipelineState:
        """Phase 1: Extract document structure"""
        try:
            markdown_structure = self.structure_extractor.extract_structure_markdown(
                state["raw_markdown"]
            )
            document_structure = self.structure_extractor.enhance_structure_with_llm(
                markdown_structure
            )
            state["document_structure"] = document_structure
        except Exception as e:
            state["processing_errors"].append(f"Structure extraction error: {str(e)}")
        
        return state
    
    def _chunk_content_node(self, state: PipelineState) -> PipelineState:
        """Phase 2: Chunk content based on structure"""
        try:
            if state["document_structure"]:
                chunked_sections = self.content_chunker.chunk_by_structure(
                    state["document_structure"], 
                    state["raw_markdown"]
                )
                state["chunked_sections"] = chunked_sections
        except Exception as e:
            state["processing_errors"].append(f"Content chunking error: {str(e)}")
        
        return state
    
    def _analyze_sections_node(self, state: PipelineState) -> PipelineState:
        """Phase 3: Analyze each section"""
        try:
            if state["chunked_sections"]:
                analyzed_sections = self.section_analyzer.analyze_all_sections(
                    state["chunked_sections"]
                )
                state["analyzed_sections"] = analyzed_sections
        except Exception as e:
            state["processing_errors"].append(f"Section analysis error: {str(e)}")
        
        return state
    
    def _merge_json_node(self, state: PipelineState) -> PipelineState:
        """Phase 4: Merge into final JSON"""
        try:
            if state["analyzed_sections"] and state["document_structure"]:
                final_json = self.json_merger.merge_analyses(
                    state["analyzed_sections"],
                    state["document_structure"]
                )
                state["final_json"] = final_json
        except Exception as e:
            state["processing_errors"].append(f"JSON merging error: {str(e)}")
        
        return state
    
    def process_invoice(self, markdown_content: str) -> PipelineState:
        """Process a markdown invoice through the entire pipeline"""
        initial_state = PipelineState(
            raw_markdown=markdown_content,
            document_structure=None,
            chunked_sections=[],
            analyzed_sections=[],
            final_json=None,
            processing_errors=[]
        )
        
        result = self.graph.invoke(initial_state)
        return result
