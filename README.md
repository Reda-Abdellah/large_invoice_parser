# Install dependencies
pip install -r requirements.txt

# Process a single invoice
python main.py examples/sample_invoice.md -o processed_invoice.json

# Process with custom config
python main.py invoice.md -c custom_config.yaml -o output.json
