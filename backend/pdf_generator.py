"""
PDF Generator for conversation export (Story-012)
Uses a fallback approach that works without system dependencies
"""

from typing import Optional
from datetime import datetime
import html

try:
    from export_models import ExportData, ExportOptions
    from jinja2 import Template
except ImportError:
    from backend.export_models import ExportData, ExportOptions
    from jinja2 import Template

# Try to import WeasyPrint, but fall back to HTML if not available
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    print("⚠️ WeasyPrint not available - PDF export will generate HTML files")


class PDFGenerator:
    """Generate PDF exports (or HTML if WeasyPrint unavailable)"""

    def __init__(self):
        """Initialize PDF generator"""
        self.use_weasyprint = WEASYPRINT_AVAILABLE

    async def generate(
        self,
        export_data: ExportData,
        options: ExportOptions
    ) -> bytes:
        """Generate PDF from export data"""

        # Build HTML from template
        html_content = self._build_html(export_data, options)

        # If WeasyPrint is available, generate PDF
        if self.use_weasyprint:
            try:
                # Apply CSS styling
                css = self._get_pdf_stylesheet(options)

                # Generate PDF
                pdf_bytes = HTML(string=html_content).write_pdf(
                    stylesheets=[CSS(string=css)]
                )

                return pdf_bytes
            except Exception as e:
                print(f"⚠️ WeasyPrint PDF generation failed: {e}")
                print("Falling back to HTML output")

        # Fallback: return HTML with embedded CSS
        return html_content.encode('utf-8')

    def _build_html(
        self,
        export_data: ExportData,
        options: ExportOptions
    ) -> str:
        """Build HTML from export data"""

        # Use Jinja2 template
        template = Template(PDF_TEMPLATE)

        # Prepare messages with escaped HTML
        messages_data = []
        for message in export_data.messages:
            msg_data = {
                'role': message.role,
                'content': self._format_content(message.content),
                'code_blocks': message.code_blocks,
                'book_references': message.book_references,
                'timestamp': message.timestamp
            }
            messages_data.append(msg_data)

        html_output = template.render(
            title=export_data.title,
            subtitle=export_data.subtitle,
            metadata=export_data.metadata,
            messages=messages_data,
            table_of_contents=export_data.table_of_contents,
            footer=export_data.footer,
            options=options,
            css=self._get_pdf_stylesheet(options)
        )

        return html_output

    def _format_content(self, content: str) -> str:
        """Format message content, escaping HTML but preserving line breaks"""
        # Escape HTML entities
        escaped = html.escape(content)
        # Convert newlines to <br> tags
        formatted = escaped.replace('\n', '<br>')
        return formatted

    def _get_pdf_stylesheet(self, options: ExportOptions) -> str:
        """Get CSS stylesheet for PDF"""

        return f"""
        @page {{
            size: {options.page_size or 'letter'};
            margin: {options.margin or '1in'};
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: {options.font_size or '11pt'};
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}

        h1 {{
            color: #1a1a1a;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
            margin-top: 0;
        }}

        h2 {{
            color: #444;
            margin-top: 30px;
        }}

        .message {{
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 8px;
            page-break-inside: avoid;
        }}

        .message.user {{
            background-color: #f0f4f8;
            border-left: 4px solid #666;
        }}

        .message.assistant {{
            background-color: #fff;
            border-left: 4px solid #0066cc;
        }}

        .message-role {{
            font-weight: bold;
            margin-bottom: 8px;
            color: #0066cc;
            font-size: 1.1em;
        }}

        .message.user .message-role {{
            color: #666;
        }}

        .timestamp {{
            color: #999;
            font-size: 0.9em;
            margin-left: 10px;
        }}

        .message-content {{
            margin: 10px 0;
            line-height: 1.6;
        }}

        pre {{
            background-color: #282c34;
            color: #abb2bf;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 10pt;
            line-height: 1.4;
            margin: 10px 0;
        }}

        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}

        .code-language {{
            color: #888;
            font-size: 0.8em;
            margin-bottom: 5px;
        }}

        .book-reference {{
            background-color: #e7f3ff;
            border-left: 4px solid #0066cc;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }}

        .book-references {{
            margin-top: 15px;
        }}

        .book-references strong {{
            display: block;
            margin-bottom: 8px;
        }}

        .metadata {{
            color: #666;
            font-size: 9pt;
            margin-bottom: 30px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }}

        .metadata p {{
            margin: 5px 0;
        }}

        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ccc;
            text-align: center;
            color: #666;
            font-size: 9pt;
        }}
        """


# PDF Template
PDF_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
    {{ css }}
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    {% if subtitle %}
    <h2>{{ subtitle }}</h2>
    {% endif %}

    <div class="metadata">
        {% if metadata.created_at %}
        <p><strong>Created:</strong>
        {% if metadata.created_at.__class__.__name__ == 'datetime' %}
            {{ metadata.created_at.strftime('%Y-%m-%d %H:%M') }}
        {% else %}
            {{ metadata.created_at }}
        {% endif %}
        </p>
        {% endif %}
        <p><strong>Messages:</strong> {{ metadata.message_count }}</p>
        {% if metadata.tags %}
        <p><strong>Tags:</strong> {{ metadata.tags|join(', ') }}</p>
        {% endif %}
    </div>

    <div class="messages">
        {% for message in messages %}
        <div class="message {{ message.role }}">
            <div class="message-role">
                {% if message.role == 'user' %}👤 User{% else %}🤖 Assistant{% endif %}
                {% if message.timestamp and options.include_timestamps %}
                <span class="timestamp">
                {% if message.timestamp.__class__.__name__ == 'datetime' %}
                    {{ message.timestamp.strftime('%H:%M') }}
                {% else %}
                    {{ message.timestamp }}
                {% endif %}
                </span>
                {% endif %}
            </div>
            <div class="message-content">
                {{ message.content|safe }}
            </div>

            {% if message.code_blocks %}
            {% for block in message.code_blocks %}
            <div class="code-language">{{ block.language }}</div>
            <pre><code>{{ block.code }}</code></pre>
            {% endfor %}
            {% endif %}

            {% if message.book_references %}
            <div class="book-references">
                <strong>📚 Referenced Books:</strong>
                {% for book in message.book_references %}
                <div class="book-reference">
                    <em>{{ book.title }}</em> by {{ book.author }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <div class="footer">
        {{ footer }}
    </div>
</body>
</html>
"""
