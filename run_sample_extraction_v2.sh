#!/bin/bash
# Batch extraction script for scanned PDFs with mode selection
# Optimized for real-world scanned documents

set -e  # Exit on error

# Configuration
API_KEY="${PDF_READER_LLM_API_KEY:-YOUR_API_KEY_HERE}"  # Set via environment variable
OUTPUT_BASE="output/position_verification_test"
PAGES="0-3"  # Process first 4 pages of each PDF

# Mode selection (change this to switch modes)
MODE="${1:-fast}"  # Default: fast, Options: fast | quality

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PDF Table Extraction for Scanned PDFs${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Set mode-specific parameters
if [ "$MODE" = "quality" ]; then
    echo -e "${CYAN}Mode: QUALITY (Consensus Voting)${NC}"
    echo -e "  • LLM attempts: 3 (with voting)"
    echo -e "  • Confidence: ✅ Enabled"
    echo -e "  • Speed: Slower (3x cost)"
    echo -e "  • Excel: Color-coded cells 🟢🟡🔴"
    CONFIG="config/scanned_quality.yaml"
    WORKER_TYPE="sequential"
    LLM_ATTEMPTS="3"
else
    echo -e "${CYAN}Mode: FAST (Single Attempt)${NC}"
    echo -e "  • LLM attempts: 1 (no voting)"
    echo -e "  • Confidence: ❌ Not available"
    echo -e "  • Speed: Faster (1x cost)"
    echo -e "  • Excel: No color coding"
    CONFIG="config/scanned_fast.yaml"
    WORKER_TYPE="thread"
    LLM_ATTEMPTS="1"
fi
echo ""

# Create output directory
mkdir -p "$OUTPUT_BASE"

# Get list of PDF files
PDF_FILES=(sample/*.pdf)
TOTAL=${#PDF_FILES[@]}

echo -e "${GREEN}Found $TOTAL PDF files to process${NC}"
echo ""

# Process each PDF
COUNTER=1
for PDF_PATH in "${PDF_FILES[@]}"; do
    # Extract filename without extension
    FILENAME=$(basename "$PDF_PATH" .pdf)
    
    echo -e "${BLUE}[$COUNTER/$TOTAL] Processing: $FILENAME${NC}"
    
    # Create output subdirectory for this PDF
    PDF_OUTPUT_DIR="$OUTPUT_BASE/$FILENAME"
    mkdir -p "$PDF_OUTPUT_DIR"
    
    # Output paths
    if [ "$MODE" = "quality" ]; then
        EXCEL_OUTPUT="$PDF_OUTPUT_DIR/${FILENAME}_tables_quality.xlsx"
    else
        EXCEL_OUTPUT="$PDF_OUTPUT_DIR/${FILENAME}_tables_fast.xlsx"
    fi
    
    # Run extraction
    echo "  Input:  $PDF_PATH"
    echo "  Output: $EXCEL_OUTPUT"
    echo "  Pages:  $PAGES"
    echo "  Config: $CONFIG"
    
    python -m pdf_reader.cli extract \
        --input "$PDF_PATH" \
        --output "$EXCEL_OUTPUT" \
        --config "$CONFIG" \
        --pages "$PAGES" \
        --llm-api-key "$API_KEY" \
        2>&1 | grep -E "(Pages processed|Tables detected|Tables extracted|confidence|error)" || true
    
    if [ -f "$EXCEL_OUTPUT" ]; then
        SIZE=$(ls -lh "$EXCEL_OUTPUT" | awk '{print $5}')
        echo -e "  ${GREEN}✓ Success! Output file: $SIZE${NC}"
    else
        echo -e "  ${YELLOW}⚠ Warning: Output file not created${NC}"
    fi
    
    echo ""
    COUNTER=$((COUNTER + 1))
done

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ All extractions complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Results saved to: $OUTPUT_BASE/"
echo ""
echo "To view output structure:"
echo "  tree $OUTPUT_BASE -L 2"
echo ""
if [ "$MODE" = "quality" ]; then
    echo -e "${CYAN}Quality mode used - Excel files have color-coded confidence!${NC}"
else
    echo -e "${YELLOW}Fast mode used - Excel files have no confidence scoring${NC}"
    echo -e "To enable confidence: Run with 'quality' mode"
    echo -e "  ./run_sample_extraction_v2.sh quality"
fi

