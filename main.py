# main.py
import sys
import yaml
import json
import argparse
from pathlib import Path
from src.pipeline.invoice_pipeline import InvoicePipeline
from typing import Dict, Any, Optional
from dataclasses import dataclass
import os

from src.utils.io import read_input_file
os.environ['NO_PROXY'] = "http://127.0.0.1,localhost,http://10.8.13.21,https://models.datalab.to,s3://text_recognition/2025_05_16"


@dataclass
class ProcessingResult:
    success: bool
    output_path: Optional[str]
    total_groups: int = 0
    total_items: int = 0
    total_amount: float = 0.0
    currency: str = "EUR"
    error: Optional[str] = None

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {str(e)}")

def process_invoice(pipeline: InvoicePipeline, 
                   input_file: str,
                   config: Dict[str, Any],
                   output_path: Optional[str] = None,
                   use_french: bool = False) -> ProcessingResult:
    """Process a single invoice file and return results"""
    try:
        # Read input file (PDF or markdown)
        markdown_content, converted_markdown_path = read_input_file(input_file, config)
        
    except Exception as e:
        return ProcessingResult(success=False, output_path=None, 
                              error=str(e))

    # Process the invoice
    print(f"Processing content ({len(markdown_content)} characters)...")
    result = pipeline.process_invoice(markdown_content)
    
    if result["processing_errors"]:
        errors = "\n".join(result["processing_errors"])
        return ProcessingResult(success=False, output_path=None, 
                              error=f"Processing errors occurred:\n{errors}",
                              )

    # Get appropriate output data
    output_data = None
    if use_french and result.get("final_json_translated"):
        output_data = result["final_json_translated"]
        suffix = "_processed_fr"
    elif result.get("structure_with_delimiters"):
        output_data = result["structure_with_delimiters"]
        suffix = "_processed"
    else:
        return ProcessingResult(success=False, output_path=None,
                              error="No valid output data generated",
                              )

    # Save results
    try:
        # Handle both dict and model objects
        if hasattr(output_data, 'model_dump'):
            output_data_dict = output_data.model_dump()
        else:
            output_data_dict = output_data
            
        output_file = output_path or f"{Path(input_file).stem}{suffix}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data_dict, f, indent=2, ensure_ascii=False, default=str)
            
        # Calculate statistics
        offer_groups = output_data_dict.get('offer_item_groups', [])
        total_groups = len(offer_groups)
        total_items = 0
        
        for group in offer_groups:
            for sub_group in group.get('offer_groups', []):
                total_items += len(sub_group.get('offer_items', []))
        
        return ProcessingResult(
            success=True,
            output_path=output_file,
            total_groups=total_groups,
            total_items=total_items,
            total_amount=output_data_dict.get('total_amount', 0),
            currency=output_data_dict.get('currency', 'EUR'),
        )
    except Exception as e:
        return ProcessingResult(success=False, output_path=None,
                              error=f"Failed to save output: {str(e)}",
                            )

def main():
    parser = argparse.ArgumentParser(description='Process PDF or markdown invoices with translation')
    parser.add_argument('input_file', help='Path to PDF or markdown invoice file')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    parser.add_argument('--config', '-c', default='config.yaml', help='Config file path')
    parser.add_argument('--no-translation', action='store_true', help='Disable translation')
    parser.add_argument('--french-output', action='store_true', help='Use French translated output')
    parser.add_argument('--save-markdown', action='store_true', help='Save converted markdown (for PDF inputs)')
    parser.add_argument('--keep-converted', action='store_true', help='Keep converted markdown file after processing')
    
    args = parser.parse_args()
    
    try:
        # Validate input file exists
        if not Path(args.input_file).exists():
            print(f"Error: Input file '{args.input_file}' does not exist")
            sys.exit(1)
        
        # Load and validate configuration
        config = load_config(args.config)
        if args.no_translation:
            config['enable_translation'] = False
        if args.save_markdown:
            config['save_converted_markdown'] = True
            
        # Initialize pipeline
        print("Initializing processing pipeline...")
        pipeline = InvoicePipeline(config)
        
        # Process invoice
        result = process_invoice(
            pipeline=pipeline,
            input_file=args.input_file,
            config=config,
            output_path=args.output,
            use_french=args.french_output
        )
        
        if result.success:
            print(f"\n✅ Processing complete!")
            print(f"📄 Output saved to: {result.output_path}")
            print(f"📊 Extracted {result.total_items} items in {result.total_groups} groups")
            if result.total_amount > 0:
                print(f"💰 Total offer amount: {result.total_amount:.2f} {result.currency}")
            
            # Handle converted markdown file
            if result.converted_markdown_path:
                if args.keep_converted:
                    print(f"📝 Converted markdown kept at: {result.converted_markdown_path}")
                else:
                    try:
                        os.remove(result.converted_markdown_path)
                        print(f"🗑️  Cleaned up temporary markdown file")
                    except Exception as e:
                        print(f"⚠️  Could not remove temporary file {result.converted_markdown_path}: {e}")
        else:
            print(f"❌ Processing failed: {result.error}")
            
            # Clean up converted markdown on failure if not keeping
            if result.converted_markdown_path and not args.keep_converted:
                try:
                    os.remove(result.converted_markdown_path)
                except:
                    pass
                    
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()