# src/pipeline/invoice_pipeline.py
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from ..models.pipeline_state import PipelineState
from ..processors.markdown_chunker import MarkdownChunker
from ..processors.structure_delimiter_extractor import StructureDelimiterExtractor
from ..processors.section_detail_analyzer import SectionDetailAnalyzer
from ..processors.translator import DocumentTranslator

class InvoicePipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize results directory
        self.results_dir = Path(config.get('results_dir', 'pipeline_results'))
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to results
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize processors
        self.markdown_chunker = MarkdownChunker(config)
        self.offer_item_extractor = StructureDelimiterExtractor(config)  # Formerly structure_extractor
        self.section_analyzer = SectionDetailAnalyzer(config)  # Update these variable names for consistency
        self.translator = DocumentTranslator(config)
        
        # Build the graph
        self.graph = self._build_graph()
        self._print_config_info()

    def _print_config_info(self):
        """Print configuration information"""
        print(f"Pipeline Configuration:")
        print(f"  Context Window Size: {self.config.get('context_window_size', 8192)} tokens")
        print(f"  Max Context Window: {self.config.get('max_context_window', 32768)} tokens")
        print(f"  Structure Model: {self.config.get('structure_model', 'llama3.2:3b')}")
        print(f"  Analysis Model: {self.config.get('analysis_model', 'llama3.2:7b')}")
        print(f"  Max Chunk Size: {self.config.get('max_chunk_size', 2000)} characters")
        print()

    def _build_graph(self) -> StateGraph:
        """Build pipeline with item detail analysis"""
        workflow = StateGraph(PipelineState)
        
        workflow.add_node("translate_to_english", self._translate_to_english_node)
        workflow.add_node("chunk_markdown", self._chunk_markdown_node)
        workflow.add_node("extract_offer_items", self._extract_structure_delimiters_node)
        workflow.add_node("analyze_item_details", self._analyze_sections_detailed_node)
        workflow.add_node("translate_to_french", self._translate_to_french_node)
        # Remove _aggregate_format_node since it's not used
        
        # Update edges accordingly
        workflow.set_entry_point("translate_to_english")
        workflow.add_edge("translate_to_english", "chunk_markdown")
        workflow.add_edge("chunk_markdown", "extract_offer_items")
        workflow.add_edge("extract_offer_items", "analyze_item_details")
        workflow.add_edge("analyze_item_details", "translate_to_french")
        workflow.add_edge("translate_to_french", END)
        
        return workflow.compile()
    
    def _translate_to_english_node(self, state: PipelineState) -> PipelineState:
        """Optional Phase 0: Translate French markdown to English"""
        try:
            if self.config.get('enable_translation', False):
                print("Phase 0: Translating document to English...")
                translated_markdown = self.translator.translate_markdown_to_english(
                    state["raw_markdown"]
                )
                state["translated_markdown"] = translated_markdown
                print(f"  Translation completed")
                # Save analysis result
                self._save_intermediate_result(
                    self._get_result_filename('0_translation'),
                    translated_markdown
                )
            else:
                print("Phase 0: Translation disabled, using original content")
                state["translated_markdown"] = None
        except Exception as e:
            state["processing_errors"].append(f"Translation to English error: {str(e)}")
            state["translated_markdown"] = None
        
        return state
    
    def _chunk_markdown_node(self, state: PipelineState) -> PipelineState:
        """Phase 1: Create overlapping chunks from markdown"""
        try:
            print("Phase 1: Creating overlapping markdown chunks...")
            
            # Use translated content if available, otherwise original
            content_to_chunk = state["translated_markdown"] or state["raw_markdown"]
            
            overlapping_chunks = self.markdown_chunker.create_overlapping_chunks(content_to_chunk)
            state["overlapping_chunks"] = overlapping_chunks
            
            # Save chunks result
            self._save_intermediate_result(
                self._get_result_filename('1_chunks'), 
                overlapping_chunks
            )
        except Exception as e:
            state["processing_errors"].append(f"Markdown chunking error: {str(e)}")
        
        return state
    
    def _extract_structure_delimiters_node(self, state: PipelineState) -> PipelineState:
        """Phase 2: Extract offer items structure"""
        try:
            if state["overlapping_chunks"]:
                structure_with_delimiters, structure_chunks = self.offer_item_extractor.extract_structure_from_chunks(
                    state["overlapping_chunks"]
                )
                state["structure_with_delimiters"] = structure_with_delimiters
                
                # Save structure result
                self._save_intermediate_result(
                    self._get_result_filename('2_structure_consolidated'),
                    structure_with_delimiters
                )
                self._save_intermediate_result(
                    self._get_result_filename('2_structure_chunks'),
                    structure_chunks
                )
        except Exception as e:
            state["processing_errors"].append(f"Structure extraction error: {str(e)}")
        
        return state
    
    def _analyze_sections_detailed_node(self, state: PipelineState) -> PipelineState:
        """Phase 3: Analyze offer items"""
        try:
            if state["structure_with_delimiters"] and state["overlapping_chunks"]:
                print("Phase 3: Analyzing individual offer items in detail...")
                
                detailed_structure = self.section_analyzer.analyze_offer_items_detailed(
                    state["structure_with_delimiters"],
                    state["overlapping_chunks"]
                )
                
                # Update the structure with detailed analysis
                state["structure_with_delimiters"] = detailed_structure

                # Save structure result
                self._save_intermediate_result(
                    self._get_result_filename('3_detailed_structure'),
                    detailed_structure
                )
                
            else:
                print("Warning: Missing structure or chunks for detailed analysis")
                
        except Exception as e:
            state["processing_errors"].append(f"Item detail analysis error: {str(e)}")
        
        return state
    
    def _translate_to_french_node(self, state: PipelineState) -> PipelineState:
        """Optional Phase 5: Translate final offer back to French"""
        try:
            if self.config.get('enable_translation', False) and state["final_json"]:
                print("Phase 5: Translating final offer back to French...")
                translated_offer = self.translator.translate_offer_to_french(
                    state["final_json"]
                )
                state["final_json_translated"] = translated_offer
                print(f"  French translation completed")
            else:
                state["final_json_translated"] = None
        except Exception as e:
            state["processing_errors"].append(f"Translation to French error: {str(e)}")
            state["final_json_translated"] = None
        
        return state
    
    def _save_intermediate_result(self, filename: str, content: Any) -> None:
        """Save intermediate results to a file"""
        # Add timestamp to filename
        timestamped_filename = f"{self.timestamp}_{filename}"
        output_path = self.results_dir / timestamped_filename
        
        try:
            if isinstance(content, (dict, list)):
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2, ensure_ascii=False, default=str)
            elif isinstance(content, bytes):
                with open(output_path, 'wb') as f:
                    f.write(content)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            print(f"Saved intermediate result to: {output_path}")
        except Exception as e:
            print(f"Error saving intermediate result: {str(e)}")

    def _get_result_filename(self, phase: str, extension: str = 'json') -> str:
        """Generate standardized filename for results"""
        return f"phase_{phase}.{extension}"
    
    def process_invoice(self, markdown_content: str) -> PipelineState:
        """Process markdown through the enhanced pipeline with translation"""
        initial_state = PipelineState(
            raw_markdown=markdown_content,
            translated_markdown=None,
            overlapping_chunks=[],
            structure_with_delimiters=None,
            section_analyses=[],
            final_json=None,
            final_json_translated=None,
            processing_errors=[]
        )
        
        print(f"Starting enhanced pipeline with {len(markdown_content)} characters...")
        result = self.graph.invoke(initial_state)
        print("Pipeline processing complete!")
        
        return result
