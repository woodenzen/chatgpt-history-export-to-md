"""Represents a single message in a conversation. It's contained in a Node object.
(it could be written in node.py, but I think it's better to separate them)

object path : conversations.json -> conversation -> mapping -> mapping node -> message
"""

from typing import Any, Dict, Optional


class Message:
    """A single message in a conversation."""

    configuration: Dict[str, Any] = {}

    def __init__(self, message: Dict[str, Any]):
        self.id = message.get("id", None)
        self.author = message.get("author", None)
        self.create_time = message.get("create_time", None)
        self.update_time = message.get("update_time", None)
        self.content = message.get("content", None)
        self.status = message.get("status", None)
        self.end_turn = message.get("end_turn", None)
        self.weight = message.get("weight", None)
        self.metadata = message.get("metadata", None)
        self.recipient = message.get("recipient", None)

    def author_role(self) -> str:
        """The role of the author of the message.

        'user', 'assistant', 'system' or 'tool'."""
        return self.author["role"]

    def author_header(self) -> str:
        """Get the title header of the message based on the configs."""
        author_config: Dict[str, Any] = self.configuration.get("author_headers", {})
        if self.author_role() == "system":
            return author_config.get("system", "### System")
        return author_config.get(self.author_role(), f"# {self.author_role().title()}")

    def content_text(self) -> str:
        """get the text content of the message."""
        if "parts" in self.content:
            return self.content["parts"][0]
        if "text" in self.content:
            return f"```python\n{self.content['text']}\n```"
        return ""

    def content_type(self) -> str:
        """get the content type of the message."""
        return self.content["content_type"]

    def model_slug(self) -> Optional[str]:
        """get the model used for the message."""
        return self.metadata.get("model_slug", None)
