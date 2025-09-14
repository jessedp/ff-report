#!/bin/bash
set -e

PREVIEW_DIR="preview"
YEAR=$(date +%Y)
WEEK=""

# Simple parsing for --week and --year
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --week)
        WEEK="$2"
        shift; shift
        ;;
        --year)
        YEAR="$2"
        shift; shift
        ;;
        *)
        shift
        ;;
    esac
done

if [ -z "$WEEK" ]; then
    echo "Please specify a week using --week <number>"
    exit 1
fi

# Setup preview directory
rm -rf $PREVIEW_DIR
mkdir -p $PREVIEW_DIR/reports

# Generate the report
OUTPUT_FILE="$PREVIEW_DIR/reports/${YEAR}-week${WEEK}.html"
python3 -m ff weekly --year $YEAR --week $WEEK --output $OUTPUT_FILE --force

# Generate reports.json
python3 build_index.py $PREVIEW_DIR/reports $PREVIEW_DIR/reports.json

# Copy viewer and assets
cp viewer/index.html viewer/style.css viewer/app.js $PREVIEW_DIR/
mkdir -p $PREVIEW_DIR/reports/logo_svg
cp -r images/logo_svg/* $PREVIEW_DIR/reports/logo_svg/
if [ -d "cache/images" ] && [ "$(ls -A cache/images)" ]; then
    cp -r cache/images/* $PREVIEW_DIR/reports/
fi
cp fball-*.png jag-*.png $PREVIEW_DIR/reports/ 2>/dev/null || true

echo "Preview for week $WEEK is ready in the '$PREVIEW_DIR' directory."

SERVER_PID=""
# Check if server is running on port 8000
if ! lsof -i:8000 -sTCP:LISTEN -t >/dev/null; then
    # Start a simple HTTP server in the background
    echo "Starting a simple HTTP server in '$PREVIEW_DIR' on port 8000..."
    (cd $PREVIEW_DIR && python3 -m http.server 8000) &
    SERVER_PID=$!
    echo "Server started with PID $SERVER_PID."
else
    echo "Server already running on port 8000. Not starting a new one."
fi

# Wait a moment for the server to start
sleep 1

# Open the report in the browser
REPORT_URL="http://localhost:8000/index.html#${YEAR}-${WEEK}"
echo "Opening $REPORT_URL in your browser..."
# xdg-open $REPORT_URL

if [ -n "$SERVER_PID" ]; then
    echo "Press Ctrl+C to stop the server."
    wait $SERVER_PID # Wait for the server process to be terminated
else
    echo "The server is running in a separate process. This script will now exit."
fi
