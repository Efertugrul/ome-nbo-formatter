#!/bin/bash
# Script to generate and validate LinkML schemas from OME XSD

set -e

# Default values
XSD_FILE="data/ome.xsd"
OUTPUT_DIR="ome_schemas"
VALIDATE=true
PARTITION=true
VERBOSE=false

# Function to display usage
usage() {
    echo "Usage: $0 [options]"
    echo "Generate LinkML schemas from OME XSD and validate them."
    echo
    echo "Options:"
    echo "  -i, --input FILE     Input XSD file (default: data/ome.xsd)"
    echo "  -o, --output DIR     Output directory for schemas (default: ome_schemas)"
    echo "  -s, --single         Generate a single schema file instead of partitioned schemas"
    echo "  -n, --no-validate    Skip schema validation"
    echo "  -v, --verbose        Enable verbose output"
    echo "  -h, --help           Display this help message"
    echo
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            XSD_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--single)
            PARTITION=false
            shift
            ;;
        -n|--no-validate)
            VALIDATE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if required files and directories exist
if [ ! -f "$XSD_FILE" ]; then
    echo "Error: XSD file not found: $XSD_FILE"
    echo "Provide a valid XSD with --input or fetch NBO via src/fetch_nbo.py"
    exit 1
fi

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "Error: Python not found. Please install Python 3.x."
    exit 1
fi

# Check if required Python packages are installed
# Note: This is a basic check and may not catch all dependencies
echo "Checking dependencies..."
python -c "import yaml" 2>/dev/null || { echo "Error: PyYAML not installed. Run 'pip install -r requirements.txt'."; exit 1; }
python -c "import lxml" 2>/dev/null || { echo "Error: lxml not installed. Run 'pip install -r requirements.txt'."; exit 1; }

# Check if LinkML is installed (only if validation is enabled)
if [ "$VALIDATE" = true ]; then
    if ! python -c "import linkml_runtime" 2>/dev/null; then
        echo "Warning: LinkML not found. Schema validation will likely fail."
        echo "Run 'pip install linkml linkml-runtime' to install LinkML."
        # Ask to continue
        read -p "Continue without LinkML? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Set verbose flag
VERBOSE_FLAG=""
if [ "$VERBOSE" = true ]; then
    VERBOSE_FLAG="--verbose"
fi

# Step 1: Generate LinkML schemas
echo "Step 1: Generating LinkML schemas..."
if [ "$PARTITION" = true ]; then
    echo "Generating partitioned schemas in $OUTPUT_DIR"
    GENERATE_CMD="python -m src.generator $XSD_FILE --output $OUTPUT_DIR --partition $VERBOSE_FLAG"
else
    echo "Generating single schema in $OUTPUT_DIR/ome.yaml"
    GENERATE_CMD="python -m src.generator $XSD_FILE --output $OUTPUT_DIR/ome.yaml $VERBOSE_FLAG"
fi

echo "Command: $GENERATE_CMD"
if ! eval "$GENERATE_CMD"; then
    echo "Error: Schema generation failed."
    exit 1
fi

echo "Schema generation completed successfully"

# Step 2: Validate schemas (if validation is enabled)
if [ "$VALIDATE" = true ]; then
    echo "Step 2: Validating generated schemas..."
    VALIDATION_REPORT="validation_report.md"
    VALIDATE_CMD="python -m src.validate_schema $OUTPUT_DIR --output $VALIDATION_REPORT $VERBOSE_FLAG"
    
    echo "Command: $VALIDATE_CMD"
    if eval "$VALIDATE_CMD"; then
        echo "Schema validation completed successfully"
        echo "All schemas are valid!"
        echo "See validation report at $VALIDATION_REPORT for details"
        echo "Pipeline completed successfully"
        exit 0
    else
        echo "Schema validation completed with errors"
        echo "See validation report at $VALIDATION_REPORT for details"
        echo "Pipeline completed with validation errors"
        exit 1
    fi
else
    echo "Schema validation skipped as requested"
    echo "Pipeline completed successfully"
    exit 0
fi 