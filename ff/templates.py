"""HTML templates for fantasy football reports"""

import os
from jinja2 import Environment, FileSystemLoader
from .config import DIV_IMAGES
from .stats import f_score


class TemplateEngine:
    """Handles HTML template rendering using Jinja2"""

    def __init__(self):
        """Initialize the template engine with the templates directory"""
        # Create the templates directory if it doesn't exist
        os.makedirs("templates", exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(loader=FileSystemLoader("templates"), autoescape=True)

        # Add custom filters
        self.env.filters["format_score"] = f_score

        # Create base template if it doesn't exist
        self.check_template_files()

    def check_template_files(self):
        """
        Checks if a static array of Jinja template files exist.

        Raises:
            FileNotFoundError: If any template file does not exist.
        """

        template_files = [
            "templates/base.jinja",
            "templates/weekly_report.jinja",
        ]

        for template_file in template_files:
            if not os.path.exists(template_file):
                raise FileNotFoundError(f"Template file not found: {template_file}")

    def render_weekly_report(self, context):
        """Render the weekly report template

        Args:
            context: Dictionary of context variables for the template

        Returns:
            Rendered HTML as string
        """
        template = self.env.get_template("weekly_report.jinja")
        return template.render(**context, div_images=DIV_IMAGES)
