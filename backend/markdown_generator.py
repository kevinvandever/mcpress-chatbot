"""
Markdown Generator for conversation export (Story-012)
"""

from typing import List
from datetime import datetime

try:
    from export_models import ExportData, ExportOptions, FormattedMessage
except ImportError:
    from backend.export_models import ExportData, ExportOptions, FormattedMessage


class MarkdownGenerator:
    """Generate Markdown exports"""

    async def generate(
        self,
        export_data: ExportData,
        options: ExportOptions
    ) -> bytes:
        """Generate Markdown from export data"""

        md_content = self._build_markdown(export_data, options)

        return md_content.encode('utf-8')

    def _build_markdown(
        self,
        export_data: ExportData,
        options: ExportOptions
    ) -> str:
        """Build Markdown content"""

        lines = []

        # Front matter (YAML)
        lines.append("---")
        lines.append(f"title: {export_data.title}")
        if export_data.subtitle:
            lines.append(f"subtitle: {export_data.subtitle}")

        # Format created_at properly
        created_at = export_data.metadata.get('created_at')
        if created_at:
            if isinstance(created_at, datetime):
                lines.append(f"created: {created_at.isoformat()}")
            else:
                lines.append(f"created: {created_at}")

        lines.append(f"messages: {export_data.metadata.get('message_count', 0)}")

        if export_data.metadata.get('tags'):
            tags_list = export_data.metadata['tags']
            lines.append(f"tags: [{', '.join(tags_list)}]")
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {export_data.title}")
        if export_data.subtitle:
            lines.append(f"## {export_data.subtitle}")
        lines.append("")

        # Metadata
        lines.append("**Conversation Details:**")

        if created_at:
            if isinstance(created_at, datetime):
                lines.append(f"- Created: {created_at.strftime('%Y-%m-%d %H:%M')}")
            else:
                lines.append(f"- Created: {created_at}")

        lines.append(f"- Messages: {export_data.metadata.get('message_count', 0)}")

        if export_data.metadata.get('tags'):
            lines.append(f"- Tags: {', '.join(export_data.metadata['tags'])}")
        if export_data.metadata.get('summary'):
            lines.append(f"\n{export_data.metadata['summary']}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Messages
        for i, message in enumerate(export_data.messages, 1):
            # Message header
            role_emoji = "👤" if message.role == "user" else "🤖"
            role_name = "User" if message.role == "user" else "Assistant"

            lines.append(f"### {role_emoji} {role_name}")

            if message.timestamp and options.include_timestamps:
                if isinstance(message.timestamp, datetime):
                    lines.append(f"*{message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*")
                else:
                    lines.append(f"*{message.timestamp}*")
            lines.append("")

            # Message content
            lines.append(message.content)
            lines.append("")

            # Book references
            if message.book_references:
                lines.append("**📚 Referenced Books:**")
                for book in message.book_references:
                    lines.append(f"- *{book.title}* by {book.author}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Footer
        lines.append("")
        lines.append(f"*{export_data.footer}*")

        return "\n".join(lines)
