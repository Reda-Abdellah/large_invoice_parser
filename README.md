# Large Invoice Parser

A comprehensive Python pipeline for processing and analyzing construction/engineering invoices and technical specifications with multi-language support and flexible LLM provider integration.

## ✨ Features

- 📄 **Multi-format Support**: Process PDF and Markdown documents seamlessly
- 🔍 **Intelligent Structure Extraction**: Hierarchical section analysis with context preservation
- 🤖 **Flexible LLM Integration**: Support for OpenAI, EdenAI, and local Ollama models
- 🔄 **Smart Chunking**: Context-aware document segmentation with overlapping chunks
- 🌐 **Multi-language Processing**: French/English translation with technical term preservation
- 💡 **Advanced Analysis**: Detailed item extraction with specifications and pricing
- 📊 **Structured Output**: Comprehensive JSON format with hierarchical organization
- ⚡ **Production Ready**: Scalable architecture with monitoring and error handling

## 🚀 Quick Start


## Installation

1. Create and activate a virtual environment:
```sh
python -m venv large_invoice_parser
source large_invoice_parser/bin/activate  # On Unix/MacOS
# or
.\large_invoice_parser\Scripts\activate  # On Windows
```

2. Install dependencies:
```sh
pip install -r requirements.txt
```

## Usage

### Basic Usage

Process a single invoice:
```sh
python main.py examples/sample_invoice.md -o processed_invoice.json
```

### Advanced Options

```sh
python main.py <input_file> [options]

Options:
  --output, -o         Output JSON file path
  --config, -c         Custom config file path (default: config.yaml)
  --no-translation     Disable translation features
  --french-output     Generate output in French
  --save-markdown     Save converted markdown for PDF inputs
  --keep-converted    Keep temporary markdown files
```

### Configuration

Create a `config.yaml` file to customize the pipeline:

```yaml
#LLM Provider Configuration

llm_providers:
structure_extraction:
provider: "edenai" # or "openai", "ollama"
model: "openai/gpt-3.5-turbo"
temperature: 0.3
api_key: "${EDENAI_API_KEY}"

detailed_analysis:
provider: "openai"
model: "gpt-4"
temperature: 0.1
api_key: "${OPENAI_API_KEY}"


#Processing Configuration
chunk_size: 4000
overlap_size: 400
context_window_size: 8192
max_context_window: 32768



#Translation Settings
enable_translation: true
source_language: "french"
target_language: "english"

#PDF Processing
save_converted_markdown: true
remove_page_numbers: true
fix_table_formatting: true
```

## Output Structure

The parser generates structured JSON output containing:
- Hierarchical section organization
- Technical specifications
- Item details and quantities
- Pricing information (when available)

## Pipeline Overview

![Invoice Processing Pipeline](figure/figure.png)

The diagram above illustrates the complete processing pipeline from input file to final JSON output, including optional translation steps and detailed analysis phases.

## Pipeline Phases

1. 🔄 Document Translation (optional)
2. 📑 Smart Content Chunking
3. 🏗️ Structure Extraction
4. 📝 Detailed Item Analysis
5. 🔄 Final Translation (optional)

## Requirements

- Python 3.11+
- See `requirements.txt` for package dependencies

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for AI and engineering industry**