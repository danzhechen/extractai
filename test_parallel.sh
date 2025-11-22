#!/bin/bash
# Test parallel vs sequential processing performance

set -e

API_KEY="${PDF_READER_LLM_API_KEY:-YOUR_API_KEY_HERE}"  # Set via environment variable
INPUT_PDF="sample/assam-1.pdf"  # 5 pages
PAGES="0-3"  # Process 4 pages

echo "=========================================="
echo "Parallel vs Sequential Performance Test"
echo "=========================================="
echo ""
echo "Test PDF: $INPUT_PDF"
echo "Pages: $PAGES"
echo ""

# Test 1: Sequential (baseline)
echo "----------------------------------------"
echo "TEST 1: Sequential Processing"
echo "----------------------------------------"
START_SEQ=$(date +%s)

python -m pdf_reader.cli extract \
  --input "$INPUT_PDF" \
  --output output/test_sequential.xlsx \
  --preset smart \
  --worker-type sequential \
  --pages "$PAGES" \
  --llm-api-key "$API_KEY" \
  2>&1 | tee output/sequential_log.txt

END_SEQ=$(date +%s)
DURATION_SEQ=$((END_SEQ - START_SEQ))

echo ""
echo "Sequential completed in: ${DURATION_SEQ}s"
echo ""

# Test 2: Thread-based parallel
echo "----------------------------------------"
echo "TEST 2: Thread-based Parallel (2 workers)"
echo "----------------------------------------"
START_THREAD=$(date +%s)

python -m pdf_reader.cli extract \
  --input "$INPUT_PDF" \
  --output output/test_parallel_thread.xlsx \
  --preset smart \
  --worker-type thread \
  --max-workers 2 \
  --pages "$PAGES" \
  --llm-api-key "$API_KEY" \
  2>&1 | tee output/thread_log.txt

END_THREAD=$(date +%s)
DURATION_THREAD=$((END_THREAD - START_THREAD))

echo ""
echo "Thread-based completed in: ${DURATION_THREAD}s"
echo ""

# Test 3: Thread-based with 4 workers
echo "----------------------------------------"
echo "TEST 3: Thread-based Parallel (4 workers)"
echo "----------------------------------------"
START_THREAD4=$(date +%s)

python -m pdf_reader.cli extract \
  --input "$INPUT_PDF" \
  --output output/test_parallel_thread4.xlsx \
  --preset smart \
  --worker-type thread \
  --max-workers 4 \
  --pages "$PAGES" \
  --llm-api-key "$API_KEY" \
  2>&1 | tee output/thread4_log.txt

END_THREAD4=$(date +%s)
DURATION_THREAD4=$((END_THREAD4 - START_THREAD4))

echo ""
echo "Thread-based (4 workers) completed in: ${DURATION_THREAD4}s"
echo ""

# Summary
echo "=========================================="
echo "Performance Summary"
echo "=========================================="
echo ""
printf "%-30s %10s\n" "Method" "Duration"
printf "%-30s %10s\n" "------" "--------"
printf "%-30s %10ss\n" "Sequential (baseline)" "$DURATION_SEQ"
printf "%-30s %10ss\n" "Thread (2 workers)" "$DURATION_THREAD"
printf "%-30s %10ss\n" "Thread (4 workers)" "$DURATION_THREAD4"
echo ""

# Calculate speedup
if [ $DURATION_SEQ -gt 0 ]; then
    SPEEDUP_2=$(echo "scale=2; $DURATION_SEQ / $DURATION_THREAD" | bc)
    SPEEDUP_4=$(echo "scale=2; $DURATION_SEQ / $DURATION_THREAD4" | bc)
    echo "Speedup with 2 workers: ${SPEEDUP_2}x"
    echo "Speedup with 4 workers: ${SPEEDUP_4}x"
fi

echo ""
echo "=========================================="
echo "Output files:"
echo "  - output/test_sequential.xlsx"
echo "  - output/test_parallel_thread.xlsx"
echo "  - output/test_parallel_thread4.xlsx"
echo "=========================================="

