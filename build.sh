#!/bin/bash

# Exit on error
set -e

# Create the distribution directory
rm -rf dist
mkdir -p dist/reports

# Generate the reports index
python3 build_index.py
mv reports.json dist/

# Copy viewer files
cp viewer/index.html dist/
cp viewer/style.css dist/
cp viewer/app.js dist/

# Copy reports
if [ -d "reports" ] && [ "$(ls -A reports)" ]; then
    cp -r reports/* dist/reports/
fi

# Copy images directly into the reports directory
if [ -d "images" ] && [ "$(ls -A images)" ]; then
    cp -r images/* dist/reports/
fi

cp fball-16x16.png dist/reports/
cp fball-32x32.png dist/reports/
cp jag-16x16.png dist/reports/


# Copy cached images
if [ -d "cache/images" ] && [ "$(ls -A cache/images)" ]; then
    cp -r cache/images/* dist/reports/
fi


# Handle LLM summary reports
SUMMARY_DIR="reports/llm_summary"
SUMMARY_LINKS_HTML=""
echo "Checking for summaries in $SUMMARY_DIR..."
if [ -d "$SUMMARY_DIR" ] && [ "$(ls -A "$SUMMARY_DIR")" ]; then
    if ! command -v pandoc &> /dev/null; then
        echo "pandoc could not be found, skipping summary generation."
    else
        echo "pandoc found. Searching for summary files..."
        SUMMARY_FILES=$(find "$SUMMARY_DIR" -name "*_llm_summary_*.md" -type f -print0 | xargs -0 ls -tr)
        
        if [ -n "$SUMMARY_FILES" ] || [ -f "prompt.txt" ]; then
            mkdir -p dist/reports/summaries
            SUMMARY_LINKS_HTML="<div class='section'><div class='section-title'>LLM Summaries & Prompt</div><hr><ol>"

            if [ -n "$SUMMARY_FILES" ]; then
                echo "Found summary files: $SUMMARY_FILES"
                for md_file in $SUMMARY_FILES; do
                    echo "Processing summary file: $md_file"
                    html_filename=$(basename "${md_file%.md}.html")
                    html_filepath="dist/reports/summaries/$html_filename"
                    echo "Outputting to: $html_filepath"

                    link_text=$html_filename
                    python3 -m ff.build_summary "$md_file" "$link_text" > "$html_filepath"

                    SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}<li><a href='summaries/$html_filename'>${link_text}</a></li>"
                done
            fi

            if [ -f "prompt.txt" ]; then
                echo "Processing prompt.txt"
                html_filename="prompt.html"
                html_filepath="dist/reports/summaries/$html_filename"
                echo "Outputting to: $html_filepath"

                link_text="prompt.txt"
                python3 -m ff.build_summary "prompt.txt" "$link_text" > "$html_filepath"

                SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}<li><a href='summaries/$html_filename'>${link_text}</a></li>"
            fi

            SUMMARY_LINKS_HTML="${SUMMARY_LINKS_HTML}</ol></div>"
        else
            echo "No summary files or prompt.txt found."
        fi
    fi
else
    echo "Summary directory '$SUMMARY_DIR' not found or is empty."
fi

# Replace placeholder in all generated reports with the links
echo "Injecting summary links into reports..."
if [ -d "dist/reports" ]; then
    replacement_file=$(mktemp)
    echo "$SUMMARY_LINKS_HTML" > "$replacement_file"

    find dist/reports -name "*.html" -type f | while read -r report_file; do
        if [[ "$report_file" != *"dist/reports/summaries/"* ]]; then
            echo "Injecting links into $report_file"
            temp_file=$(mktemp)
            sed -e "/<!-- SUMMARY_REPORTS_PLACEHOLDER -->/r $replacement_file" -e "s/<!-- SUMMARY_REPORTS_PLACEHOLDER -->//g" "$report_file" > "$temp_file"
            mv "$temp_file" "$report_file"
        fi
    done
    rm "$replacement_file"
    echo "Injection complete."
else
    echo "dist/reports directory not found for link injection."
fi

echo "Build complete. The 'dist' directory is ready for deployment."