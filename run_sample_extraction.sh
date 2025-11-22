#!/bin/bash
# Batch extraction script for all sample PDFs with position verification
# Output organized in separate folders

set -e  # Exit on error

# Configuration
API_KEY="${PDF_READER_LLM_API_KEY:-YOUR_API_KEY_HERE}"  # Set via environment variable
OUTPUT_BASE="output/position_verification_test"
PRESET="smart"
WORKER_TYPE="sequential"
PAGES="0-3"  # Process first 4 pages of each PDF

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PDF Table Extraction with Position Verification${NC}"
echo -e "${BLUE}========================================${NC}"
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
    EXCEL_OUTPUT="$PDF_OUTPUT_DIR/${FILENAME}_tables.xlsx"
    
    # Run extraction
    echo "  Input:  $PDF_PATH"
    echo "  Output: $EXCEL_OUTPUT"
    echo "  Pages:  $PAGES"
    
    python -m pdf_reader.cli extract \
        --input "$PDF_PATH" \
        --output "$EXCEL_OUTPUT" \
        --preset "$PRESET" \
        --worker-type "$WORKER_TYPE" \
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
echo "Output structure:"
tree -L 2 "$OUTPUT_BASE" 2>/dev/null || ls -R "$OUTPUT_BASE"

