"""
Just a placeholder for now.
a bunch of classes and functions to handle conversations, messages, stats, etc.

object path : conversations.json -> conversation (one of the list items)
"""

import re
from datetime import datetime, timedelta
from time import ctime
from typing import Any, Dict, List, Optional

from utils.utils import ensure_closed_code_blocks, replace_latex_delimiters

from .node import Node


class Conversation:
    """Stores the conversation object from the conversations.json file."""

    configuration: Dict[str, Any] = {}

    def __init__(self, conversation: Dict[str, Any]):
        self.title = conversation.get("title", None)
        self.create_time = conversation.get("create_time", None)
        self.update_time = conversation.get("update_time", None)
        self.mapping = Node.nodes_from_mapping(conversation.get("mapping", None))
        self.moderation_results = conversation.get("moderation_results", None)
        self.current_node = self.mapping[conversation.get("current_node", None)]
        self.plugin_ids = conversation.get("plugin_ids", None)
        self.conversation_id = conversation.get("conversation_id", None)
        self.conversation_template_id = conversation.get(
            "conversation_template_id", None
        )
        self.id = conversation.get("id", None)

    def chat_link(self) -> str:
        """Chat URL.

        Links to the original chat, not a 'shared' one. Needs user's login to chat.openai.com.
        """
        return f"https://chat.openai.com/c/{self.conversation_id}"

    def _main_branch_nodes(self) -> List[Node]:
        """List of all nodes that have a message in the current 'main' branch.

        the 'current_node' represents the last node in the main branch."""

        nodes: List[Node] = []
        curr_node = self.current_node
        curr_parent = curr_node.parent

        while curr_parent:
            if curr_node.message:
                nodes.append(curr_node)
            curr_node = curr_parent
            curr_parent = curr_node.parent

        nodes.reverse()

        return nodes

    def _all_message_nodes(self) -> List[Node]:
        """List of all nodes that have a message in the conversation, including all branches."""

        nodes: List[Node] = []
        for _, node in self.mapping.items():
            if node.message:
                nodes.append(node)

        return nodes

    def has_multiple_branches(self) -> bool:
        """Check if the conversation has multiple branches."""
        return len(self._all_message_nodes()) > len(self._main_branch_nodes())

    def leaf_count(self) -> int:
        """Number of leaves in the conversation."""
        return sum(1 for node in self._all_message_nodes() if not node.children)

    def content_types(self) -> List[str]:
        """List of all content types in the conversation. (all branches)

        (e.g. text, code, execution_output, etc.)"""
        return list(
            set(
                node.message.content_type()
                for node in self._all_message_nodes()
                if node.message
            )
        )

    def message_count(self) -> int:
        """Number of 'user' and 'assistant' messages in the conversation. (all branches)"""
        return sum(
            1
            for node in self._all_message_nodes()
            if node.message and node.message.author_role() in ("user", "assistant")
        )

    def user_message_timestamps(self) -> List[float]:
        """List of all 'user' message timestamps in the conversation.
        (all branches) Useful for generating time series plots."""
        return [node.message.create_time for node in self._user_nodes() if node.message]

    def assistant_message_timestamps(self) -> List[float]:
        """List of all 'assistant' message timestamps in the conversation.
        (all branches) Useful for generating time series plots."""
        return [
            node.message.create_time for node in self._assistant_nodes() if node.message
        ]

    def _system_nodes(self) -> List[Node]:
        """List of all 'system' nodes in the conversation. (all branches)"""
        return [
            node
            for node in self._all_message_nodes()
            if node.message and node.message.author_role() == "system"
        ]

    def _user_nodes(self) -> List[Node]:
        """List of all 'user' nodes in the conversation. (all branches)"""
        return [
            node
            for node in self._all_message_nodes()
            if node.message and node.message.author_role() == "user"
        ]

    def _assistant_nodes(self) -> List[Node]:
        """List of all 'assistant' nodes in the conversation. (all branches)"""
        return [
            node
            for node in self._all_message_nodes()
            if node.message and node.message.author_role() == "assistant"
        ]

    def _tool_nodes(self) -> List[Node]:
        """List of all 'tool' nodes in the conversation. (all branches)"""
        return [
            node
            for node in self._all_message_nodes()
            if node.message and node.message.author_role() == "tool"
        ]

    def entire_user_text(self) -> str:
        """Entire raw 'user' text in the conversation. (all branches)

        Useful for generating word clouds."""
        return "\n".join(
            node.message.content_text() for node in self._user_nodes() if node.message
        )

    def entire_assistant_text(self) -> str:
        """Entire raw 'assistant' text in the conversation. (all branches)

        Useful for generating word clouds."""
        return "\n".join(
            node.message.content_text()
            for node in self._assistant_nodes()
            if node.message
        )

    def model_slug(self) -> Optional[str]:
        """ChatGPT model used for the conversation."""
        assistant_nodes = self._assistant_nodes()
        if not assistant_nodes:
            return None

        message = assistant_nodes[0].message
        if not message:
            return None

        return message.model_slug()

    def used_plugins(self) -> List[str]:
        """List of all ChatGPT plugins used in the conversation."""
        return list(
            set(
                node.message.metadata["invoked_plugin"]["namespace"]
                for node in self._tool_nodes()
                if node.message and node.message.metadata.get("invoked_plugin")
            )
        )

    def custom_instructions(self) -> Optional[Dict[str, str]]:
        """Custom instructions used for the conversation."""
        if len(self._system_nodes()) < 2:
            return None
        context_message = self._system_nodes()[1].message
        if context_message and context_message.metadata.get(
            "is_user_system_message", None
        ):
            return context_message.metadata.get("user_context_message_data", None)
        return None

        # TODO: check if this is the same for conversations from the bookmarklet download

    def yaml_header(self) -> str:
        """YAML metadata header for the conversation."""
        yaml_config = self.configuration.get("yaml", {})

        yaml_map = {
            "title": self.title,
            "chat_link": self.chat_link(),
            "create_time": ctime(self.create_time),
            "update_time": ctime(self.update_time),
            "model": self.model_slug(),
            "used_plugins": self.used_plugins(),
            "message_count": self.message_count(),
            "content_types": self.content_types(),
            "custom_instructions": self.custom_instructions(),
        }

        yaml = "---\n"

        for key, value in yaml_map.items():
            if yaml_config.get(key, True):
                yaml += f"{key}: {value}\n"

        yaml += "---\n"

        return yaml

    def _branch_indicator(self, node: Node) -> str:
        """Get the branch indicator for the given node."""
        if node in self._main_branch_nodes():
            return "(main branch ⎇)"
        return "(other branch ⎇)"

        # TODO: placeholder for now, to be implemented later

    def file_text_content(self) -> str:
        """Returns the full markdown text content of the conversation."""
        markdown_config = self.configuration.get("markdown", {})
        latex_delimiters = markdown_config.get("latex_delimiters", "default")

        markdown = self.yaml_header()

        for node in self._all_message_nodes():
            if node.message:
                content = ensure_closed_code_blocks(node.message.content_text())
                # prevent empty messages from taking up white space
                content = f"\n{content}\n" if content else ""
                if latex_delimiters == "dollar sign":
                    content = replace_latex_delimiters(content)
                markdown += (
                    f"\n{self._branch_indicator(node)}\n"
                    f"{node.header()}{content}{node.footer()}\n---\n"
                )
        return markdown

    def stats(self) -> Dict[str, Any]:
        """Get diverse insightful stats on the conversation."""
        return {}

        # TODO: add stats

    def file_name(self) -> str:
        """Sanitized title of the conversation, compatible with file names."""
        file_anti_pattern = re.compile(r'[<>:"/\\|?*\n\r\t\f\v]')
        return file_anti_pattern.sub("_", self.title) if self.title else "untitled"

    def start_of_year(self) -> datetime:
        """Returns the first of January of the year the conversation was created in,
        as a datetime object."""
        return datetime(datetime.fromtimestamp(self.create_time).year, 1, 1)

    def start_of_month(self) -> datetime:
        """Returns the first of the month the conversation was created in,
        as a datetime object."""
        return datetime(
            datetime.fromtimestamp(self.create_time).year,
            datetime.fromtimestamp(self.create_time).month,
            1,
        )

    def start_of_week(self) -> datetime:
        """Returns the monday of the week the conversation was created in,
        as a datetime object."""
        start_of_week = datetime.fromtimestamp(self.create_time) - timedelta(
            days=datetime.fromtimestamp(self.create_time).weekday()
        )
        return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
