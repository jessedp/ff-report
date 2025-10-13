#!/bin/bash

# Exit on error
set -e

# --- Configuration ---
PREVIEW_DEST_DIR="preview"
BUILD_DEST_DIR="dist"
SUMMARY_SRC_DIR="reports/llm_summary"

# --- Argument Parsing ---
MODE="preview"
if [ "$1" == "build" ]; then
    MODE="build"
    shift
fi

if [ "$MODE" == "preview" ]; then
    DEST_DIR=$PREVIEW_DEST_DIR
else # build mode
    DEST_DIR=$BUILD_DEST_DIR
fi

YEAR=$(date +%Y)
WEEK=""
# Simple parsing for --week and --year
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --week) WEEK="$2"; shift; shift;;
        --year) YEAR="$2"; shift; shift;;
        *)
        shift
        ;;
    esac
done

# Check if WEEK is set for preview mode after parsing all arguments
if [ "$MODE" == "preview" ] && [ -z "$WEEK" ]; then
    echo "Preview mode requires --week <number>"
    exit 1
fi

# --- Main Logic ---

# 1. Setup destination directory
echo "--- Cleaning and creating destination directory: $DEST_DIR ---"
rm -rf $DEST_DIR
mkdir -p $DEST_DIR/reports

# 2. Generate/Copy reports
if [ "$MODE" == "build" ]; then
    if [ -n "$WEEK" ]; then # If WEEK is provided, generate a single report
        echo "--- Generating BUILD report for Week $WEEK, Year $YEAR ---"
        # OUTPUT_FILE="$DEST_DIR/reports/${YEAR}-week${WEEK}.html"
        python3 -m ff --verbose weekly --year $YEAR --week $WEEK
    else # If WEEK is not provided, generate all reports (placeholder for now)
        echo "--- Generating ALL reports for Year $YEAR (Not yet implemented) ---"
    fi
    if [ -d "reports" ] && [ "$(ls -A reports)" ]; then
        cp -r reports/* $DEST_DIR/reports/
    fi
else # preview mode
    echo "--- Generating PREVIEW report for Week $WEEK, Year $YEAR ---"
    OUTPUT_FILE="$DEST_DIR/reports/${YEAR}-week${WEEK}.html"
    python3 -m ff --verbose weekly --year $YEAR --week $WEEK --output $OUTPUT_FILE --force
fi

# 3. Copy common assets
echo "--- Copying assets ---"
cp viewer/index.html viewer/style.css viewer/app.js $DEST_DIR/
cp fball-*.png jag-*.png $DEST_DIR/reports/ 2>/dev/null || true
if [ -d "images" ]; then
    cp -r images/* $DEST_DIR/reports/
fi
if [ -d "cache/images" ]; then
    cp -r cache/images/* $DEST_DIR/reports/
fi

# 4. Generate LLM Summary if needed (for build mode)
if [ "$MODE" == "build" ] && [ -n "$WEEK" ]; then
    LLM_SUMMARY_FILE="$SUMMARY_SRC_DIR/${YEAR}-week${WEEK}_llm_summary.md"
    if [ ! -f "$LLM_SUMMARY_FILE" ]; then
        echo "--- LLM Summary for Week $WEEK not found, generating... ---"
        python3 -m ff.llm_report --week $WEEK --year $YEAR
    else
        echo "--- LLM Summary for Week $WEEK already exists. ---"
    fi
fi

# 4. Handle LLM Summaries
echo "--- Handling LLM Summaries ---"
SUMMARY_LINKS_HTML=""
if [ -d "$SUMMARY_SRC_DIR" ] && [ "$(ls -A "$SUMMARY_SRC_DIR")" ]; then
    if ! command -v pandoc &> /dev/null; then
        echo "pandoc not found, skipping summary generation."
    else
        echo "pandoc found. Searching for summary files..."

        find_pattern="*_llm_summary.md"
        if [ "$MODE" == "preview" ] || ([ "$MODE" == "build" ] && [ -n "$WEEK" ]); then
            find_pattern="${YEAR}-week${WEEK}_llm_summary.md"
        fi
        SUMMARY_FILES=$(find "$SUMMARY_SRC_DIR" -name "$find_pattern" -type f -print0 | xargs -0)

        if [ -n "$SUMMARY_FILES" ] || [ -f "prompt.txt" ]; then
            mkdir -p "$DEST_DIR/reports/summaries"
            SUMMARY_LINKS_HTML="<div class='section'><div class='section-title'>LLM Summaries & Prompt</div><hr><ol>"

            if [ -n "$SUMMARY_FILES" ]; then
                for md_file in $SUMMARY_FILES; do
                    html_filename=$(basename "${md_file%.md}.html")
                    html_filepath="$DEST_DIR/reports/summaries/$html_filename"
                    link_text=$html_filename
                    python3 -m ff.build_summary "$md_file" "$link_text" > "$html_filepath"
                    SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}<li><a href='summaries/$html_filename'>${link_text}</a></li>"
                done
            fi

            if [ -f "prompt.txt" ]; then
                html_filename="prompt.html"
                html_filepath="$DEST_DIR/reports/summaries/$html_filename"
                link_text="prompt.txt"
                python3 -m ff.build_summary "prompt.txt" "$link_text" > "$html_filepath"
                SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}<li><a href='summaries/$html_filename'>${link_text}</a></li>"
            fi

            SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}</ol></div>"
        fi
    fi
fi

# 5. Inject LLM links
if [ -n "$SUMMARY_LINKS_HTML" ]; then
    echo "--- Injecting summary links into reports ---"
    replacement_file=$(mktemp)
    echo "$SUMMARY_LINKS_HTML" > "$replacement_file"

    if [ "$MODE" == "preview" ]; then
        # Inject into the single generated file
        if [ -f "$OUTPUT_FILE" ]; then
            temp_file=$(mktemp)
            sed -e "/<!-- SUMMARY_REPORTS_PLACEHOLDER -->/r $replacement_file" -e "s/<!-- SUMMARY_REPORTS_PLACEHOLDER -->//g" "$OUTPUT_FILE" > "$temp_file"
            mv "$temp_file" "$OUTPUT_FILE"
        fi
    else # build
        # Inject into all report files
        find "$DEST_DIR/reports" -name "*.html" -type f | while read -r report_file; do
            if [[ "$report_file" != *"/summaries/"* ]]; then
                temp_file=$(mktemp)
                sed -e "/<!-- SUMMARY_REPORTS_PLACEHOLDER -->/r $replacement_file" -e "s/<!-- SUMMARY_REPORTS_PLACEHOLDER -->//g" "$report_file" > "$temp_file"
                mv "$temp_file" "$report_file"
            fi
        done
    fi
    rm "$replacement_file"
fi

# 6. Generate index
echo "--- Generating reports index ---"
if [ "$MODE" == "preview" ]; then
    python3 build_index.py $DEST_DIR/reports $DEST_DIR/reports.json
else # build
    python3 build_index.py
    mv reports.json $DEST_DIR/
fi

# 7. Final steps (server for preview)
if [ "$MODE" == "preview" ]; then
    echo "--- Starting preview server ---"
    echo "Preview for week $WEEK is ready in the '$DEST_DIR' directory."
    SERVER_PID=""
    if ! lsof -i:8000 -sTCP:LISTEN -t >/dev/null; then
        (cd $DEST_DIR && python3 -m http.server 8000) &
        SERVER_PID=$!
        echo "Server started with PID $SERVER_PID."
    else
        echo "Server already running on port 8000."
    fi
    sleep 1
    REPORT_URL="http://localhost:8000/index.html#${YEAR}-${WEEK}"
    echo "Opening $REPORT_URL in your browser..."
    # xdg-open $REPORT_URL
    if [ -n "$SERVER_PID" ]; then
        echo "Press Ctrl+C to stop the server."
        wait $SERVER_PID
    else
        echo "The server is running in a separate process. This script will now exit."
    fi
else
    echo "Build complete. The '$DEST_DIR' directory is ready for deployment."
fi
