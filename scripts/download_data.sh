#!/bin/bash
# Download and prepare the Instacart dataset
#
# This script provides a clear entry point for data acquisition.
# It wraps the Python ingestion script with helpful guidance.

set -e

echo "================================================================"
echo "Instacart Dataset Download"
echo "================================================================"
echo ""
echo "This script downloads the Instacart Market Basket Analysis"
echo "dataset from Kaggle (207 MB) and prepares it for analysis."
echo ""

# Check if Kaggle credentials are configured
if [ ! -f ~/.kaggle/access_token ] && [ -z "$KAGGLE_API_TOKEN" ]; then
    echo "❌ Kaggle API credentials not found"
    echo ""
    echo "To download the dataset, you need to authenticate with Kaggle:"
    echo ""
    echo "  1. Go to: https://www.kaggle.com/settings/account"
    echo "  2. Scroll to 'API' section and generate a token (KGAT_...)"
    echo "  3. Choose one:"
    echo ""
    echo "     Option A: Export as environment variable (this session only)"
    echo "       export KAGGLE_API_TOKEN=KGAT_your_token_here"
    echo ""
    echo "     Option B: Save to file (persists across sessions)"
    echo "       mkdir -p ~/.kaggle"
    echo "       echo 'KGAT_your_token_here' > ~/.kaggle/access_token"
    echo "       chmod 600 ~/.kaggle/access_token"
    echo ""
    echo "  4. Then re-run this script"
    echo ""
    echo "Alternative: Manual download"
    echo "  1. Visit: https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis"
    echo "  2. Click 'Download' button"
    echo "  3. Extract ZIP to data/raw/"
    echo "  4. Run: python scripts/ingest_data.py --skip-download"
    echo ""
    exit 1
fi

echo "✓ Kaggle credentials found"
echo ""
echo "Starting download and conversion..."
echo ""

# Run the Python ingestion script
python scripts/ingest_data.py

echo ""
echo "================================================================"
echo "✓ Dataset ready!"
echo "================================================================"
echo ""
echo "Downloaded: data/raw/*.csv (207 MB)"
echo "Processed:  data/processed/*.parquet (faster, compressed)"
echo ""
echo "Next steps:"
echo "  - Run data audit:     python scripts/audit_data.py"
echo "  - Build sequences:    python scripts/build_sequences_batched.py"
echo "  - See README.md for full analysis pipeline"
echo ""
