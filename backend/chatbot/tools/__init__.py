"""
LangChain Tools for LISA AI
Content generator, FAQ retriever, and partner analytics
"""

from .content_generator import generate_marketing_content
from .faq_retriever import lookup_faq
from .partner_analytics import analyze_partner_behavior


def get_tools():
    """Return all available LangChain tools."""
    return [generate_marketing_content, lookup_faq, analyze_partner_behavior]


def get_tool_by_name(name):
    """Get a specific tool by its name."""
    tools_map = {
        "generate_marketing_content": generate_marketing_content,
        "lookup_faq": lookup_faq,
        "analyze_partner_behavior": analyze_partner_behavior,
    }
    return tools_map.get(name)
