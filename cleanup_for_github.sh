#!/bin/bash
# Cleanup script for preparing repository for GitHub

echo "Cleaning up repository for GitHub..."
echo ""

# Remove Python cache files
echo "→ Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# Remove macOS files
echo "→ Removing macOS system files..."
find . -name ".DS_Store" -delete 2>/dev/null || true

# Remove pytest cache
echo "→ Removing pytest cache..."
rm -rf .pytest_cache/ 2>/dev/null || true
rm -rf tests/.pytest_cache/ 2>/dev/null || true

# Remove output files
echo "→ Removing output files..."
rm -rf output/ 2>/dev/null || true
rm -rf debug_output/ 2>/dev/null || true
rm -f *.xlsx 2>/dev/null || true
rm -f *.log 2>/dev/null || true
rm -f *_log.txt 2>/dev/null || true

# Remove temporary test files
echo "→ Removing temporary files..."
rm -f --output 2>/dev/null || true

# Clean up egg-info
echo "→ Removing build artifacts..."
rm -rf *.egg-info 2>/dev/null || true
rm -rf build/ dist/ 2>/dev/null || true

echo ""
echo "✓ Cleanup complete!"
echo ""
echo "Files remaining:"
du -sh . 2>/dev/null || true
echo ""
echo "Ready for git commit!"

