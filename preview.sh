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

# Handle LLM summary reports for the previewed week
SUMMARY_DIR="reports/llm_summary"
SUMMARY_LINKS_HTML=""
echo "Checking for summaries in $SUMMARY_DIR for week $WEEK of $YEAR..."
if [ -d "$SUMMARY_DIR" ] && [ "$(ls -A "$SUMMARY_DIR")" ]; then
    if ! command -v pandoc &> /dev/null; then
        echo "pandoc could not be found, skipping summary generation."
    else
        echo "pandoc found. Searching for summary files..."
        SUMMARY_FILES=$(find $SUMMARY_DIR -name "${YEAR}-week${WEEK}*_llm_summary_*.md" -type f -print0 | xargs -0 ls -tr)
        
        if [ -n "$SUMMARY_FILES" ] || [ -f "prompt.txt" ]; then
            mkdir -p $PREVIEW_DIR/reports/summaries
            SUMMARY_LINKS_HTML="<div class='section'><div class='section-title'>LLM Summaries & Prompt</div><hr><ol>"

            if [ -n "$SUMMARY_FILES" ]; then
                echo "Found summary files: $SUMMARY_FILES"
                for md_file in $SUMMARY_FILES; do
                    echo "Processing summary file: $md_file"
                    html_filename=$(basename "${md_file%.md}.html")
                    html_filepath="$PREVIEW_DIR/reports/summaries/$html_filename"
                    echo "Outputting to: $html_filepath"

                    link_text=$html_filename
                    python3 -m ff.build_summary "$md_file" "$link_text" > "$html_filepath"

                    SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}<li><a href='summaries/$html_filename'>${link_text}</a></li>"
                done
            fi

            if [ -f "prompt.txt" ]; then
                echo "Processing prompt.txt"
                html_filename="prompt.html"
                html_filepath="$PREVIEW_DIR/reports/summaries/$html_filename"
                echo "Outputting to: $html_filepath"

                link_text="prompt.txt"
                python3 -m ff.build_summary "prompt.txt" "$link_text" > "$html_filepath"

                SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}<li><a href='summaries/$html_filename'>${link_text}</a></li>"
            fi

            SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}</ol></div>"
        else
            echo "No summary files or prompt.txt found for this week."
        fi
    fi
else
    echo "Summary directory '$SUMMARY_DIR' not found or is empty."
fi

# Replace placeholder in the generated report
echo "Injecting summary links into report..."
if [ -f "$OUTPUT_FILE" ]; then
    replacement_file=$(mktemp)
    echo "$SUMMARY_LINKS_HTML" > "$replacement_file"
    temp_file=$(mktemp)
    sed -e "/<!-- SUMMARY_REPORTS_PLACEHOLDER -->/r $replacement_file" -e "s/<!-- SUMMARY_REPORTS_PLACEHOLDER -->//g" "$OUTPUT_FILE" > "$temp_file"
    mv "$temp_file" "$OUTPUT_FILE"
    rm "$replacement_file"
    echo "Injection complete."
else
    echo "Output file '$OUTPUT_FILE' not found for link injection."
fi

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