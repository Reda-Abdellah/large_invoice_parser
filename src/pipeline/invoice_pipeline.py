# src/pipeline/invoice_pipeline.py
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from ..models.pipeline_state import PipelineState
from ..processors.markdown_chunker import MarkdownChunker
from ..processors.structure_delimiter_extractor import StructureDelimiterExtractor
from ..processors.section_detail_analyzer import SectionDetailAnalyzer
from ..processors.offer_aggregator import OfferAggregator

class InvoicePipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize processors
        self.markdown_chunker = MarkdownChunker(config)
        self.structure_extractor = StructureDelimiterExtractor(config)
        self.section_analyzer = SectionDetailAnalyzer(config)
        self.offer_aggregator = OfferAggregator(config)
        
        # Build the graph
        self.graph = self._build_graph()
        self._print_config_info()
    
    def _print_config_info(self):
        """Print configuration information"""
        print(f"New Pipeline Configuration:")
        print(f"  Chunk Size: {self.config.get('chunk_size', 4000)} characters")
        print(f"  Overlap Size: {self.config.get('overlap_size', 400)} characters")
        print(f"  Context Window: {self.config.get('context_window_size', 8192)} tokens")
        print(f"  Structure Model: {self.config.get('structure_model', 'llama3.2:3b')}")
        print(f"  Analysis Model: {self.config.get('analysis_model', 'llama3.2:7b')}")
        print()
    
    def _build_graph(self) -> StateGraph:
        """Build the new 4-phase pipeline"""
        workflow = StateGraph(PipelineState)
        
        # Add nodes for new pipeline
        workflow.add_node("chunk_markdown", self._chunk_markdown_node)
        workflow.add_node("extract_structure_delimiters", self._extract_structure_delimiters_node)
        workflow.add_node("analyze_sections_detailed", self._analyze_sections_detailed_node)
        workflow.add_node("aggregate_format", self._aggregate_format_node)
        
        # Add edges
        workflow.set_entry_point("chunk_markdown")
        workflow.add_edge("chunk_markdown", "extract_structure_delimiters")
        workflow.add_edge("extract_structure_delimiters", "analyze_sections_detailed")
        workflow.add_edge("analyze_sections_detailed", "aggregate_format")
        workflow.add_edge("aggregate_format", END)
        
        return workflow.compile()
    
    def _chunk_markdown_node(self, state: PipelineState) -> PipelineState:
        """Phase 1: Create overlapping chunks from markdown"""
        try:
            print("Phase 1: Creating overlapping markdown chunks...")
            overlapping_chunks = self.markdown_chunker.create_overlapping_chunks(
                state["raw_markdown"]
            )
            state["overlapping_chunks"] = overlapping_chunks
            # Save enhanced structure
        except Exception as e:
            state["processing_errors"].append(f"Markdown chunking error: {str(e)}")
        
        return state
    
    def _extract_structure_delimiters_node(self, state: PipelineState) -> PipelineState:
        """Phase 2: Extract structure with delimiters"""
        try:
            if state["overlapping_chunks"]:
                structure_with_delimiters = self.structure_extractor.extract_structure_from_chunks(
                    state["overlapping_chunks"]
                )
                state["structure_with_delimiters"] = structure_with_delimiters
        except Exception as e:
            state["processing_errors"].append(f"Structure extraction error: {str(e)}")
        
        return state
    
    def _analyze_sections_detailed_node(self, state: PipelineState) -> PipelineState:
        """Phase 3: Detailed section-by-section analysis"""
        try:
            if state["structure_with_delimiters"]:
                section_analyses = self.section_analyzer.analyze_sections_detailed(
                    state["structure_with_delimiters"],
                    state["raw_markdown"]
                )
                state["section_analyses"] = section_analyses
        except Exception as e:
            state["processing_errors"].append(f"Section analysis error: {str(e)}")
        
        return state
    
    def _aggregate_format_node(self, state: PipelineState) -> PipelineState:
        """Phase 4: Aggregate and format final offer"""
        try:
            if state["section_analyses"]:
                final_json = self.offer_aggregator.aggregate_and_format(
                    state["section_analyses"]
                )
                state["final_json"] = final_json
        except Exception as e:
            state["processing_errors"].append(f"Aggregation error: {str(e)}")
        
        return state
    
    def process_invoice(self, markdown_content: str) -> PipelineState:
        """Process markdown through the new 4-phase pipeline"""
        initial_state = PipelineState(
            raw_markdown=markdown_content,
            overlapping_chunks=[],
            structure_with_delimiters=None,
            section_analyses=[],
            final_json=None,
            processing_errors=[]
        )
        
        print(f"Starting new pipeline with {len(markdown_content)} characters...")
        result = self.graph.invoke(initial_state)
        print("Pipeline processing complete!")
        
        return result
