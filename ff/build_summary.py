import sys
import pypandoc
from jinja2 import Environment, FileSystemLoader


def build_summary(markdown_file, title):
    """
    Reads a markdown file, converts it to HTML, and renders it into
    the summary.jinja template.
    """
    try:
        with open(markdown_file, "r", encoding="utf-8") as f:
            md_content = f.read()
    except FileNotFoundError:
        sys.stderr.write(f"Error: Markdown file not found at {markdown_file}\n")
        sys.exit(1)

    try:
        # Convert markdown to HTML using pypandoc
        html_content = pypandoc.convert_text(md_content, "html", format="md")
    except OSError:
        sys.stderr.write(
            "Error: pandoc not found. Please install pandoc and add it to your PATH.\n"
        )
        # Return a simple HTML error message to be rendered
        html_content = "<h1>Error: pandoc not found</h1><p>Please install pandoc to view this summary.</p>"

    # Setup Jinja environment
    env = Environment(loader=FileSystemLoader("templates"))

    # Get the template
    template = env.get_template("summary.jinja")

    # Create the context
    context = {"title": title, "content": html_content}

    # Render the final HTML
    output_html = template.render(context)

    print(output_html)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m ff.build_summary <markdown_file> <title>")
        sys.exit(1)

    markdown_file_path = sys.argv[1]
    report_title = sys.argv[2]
    build_summary(markdown_file_path, report_title)
