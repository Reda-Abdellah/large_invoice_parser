# main.py
import yaml
import json
import argparse
from pathlib import Path
from src.pipeline.invoice_pipeline import InvoicePipeline
import os
os.environ['NO_PROXY'] = "http://127.0.0.1,localhost,http://10.8.13.21"


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    parser = argparse.ArgumentParser(description='Process markdown invoices with translation')
    parser.add_argument('input_file', help='Path to markdown invoice file')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    parser.add_argument('--config', '-c', default='config.yaml', help='Config file path')
    parser.add_argument('--no-translation', action='store_true', help='Disable translation')
    parser.add_argument('--french-output', action='store_true', help='Use French translated output')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override translation setting if specified
    if args.no_translation:
        config['enable_translation'] = False
    
    # Initialize pipeline
    pipeline = InvoicePipeline(config)
    
    # Read input file
    with open(args.input_file, 'r', encoding='utf-8') as file:
        markdown_content = file.read()
    
    print(f"Processing invoice: {args.input_file}")
    
    # Process the invoice
    result = pipeline.process_invoice(markdown_content)
    
    # Handle results
    if result["processing_errors"]:
        print("Processing errors occurred:")
        for error in result["processing_errors"]:
            print(f"  - {error}")
    
    # Choose output (French translated or English)
    final_output = None
    output_suffix = "_processed"
    
    if args.french_output and result["final_json_translated"]:
        final_output = result["final_json_translated"]
        output_suffix = "_processed_fr"
        print("Using French translated output")
    elif result["final_json"]:
        final_output = result["final_json"]
        output_suffix = "_processed_en" if config.get('enable_translation') else "_processed"
        print("Using English output")
    
    if final_output:
        # Convert to dict for JSON serialization
        output_data = final_output.model_dump()
        
        # Save to file
        output_path = args.output or f"{Path(args.input_file).stem}{output_suffix}.json"
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(output_data, file, indent=2, ensure_ascii=False, default=str)
        
        print(f"Processing complete! Output saved to: {output_path}")
        
        # Summary statistics
        total_groups = len(output_data['offer_item_groups'])
        total_items = sum(len(group['offer_items']) for group in output_data['offer_item_groups'])
        total_amount = output_data.get('total_amount', 0)
        
        print(f"Extracted {total_items} items in {total_groups} groups")
        print(f"Total offer amount: {total_amount:.2f} {output_data.get('currency', 'EUR')}")
    else:
        print("Processing failed - no output generated")

if __name__ == "__main__":
    main()