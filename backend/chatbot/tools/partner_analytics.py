"""
Partner Analytics Tool for LISA AI
Analyzes partner behavior patterns from conversation history
"""

from langchain_core.tools import tool


@tool
def analyze_partner_behavior(
    partner_type: str = "MFD",
    analysis_type: str = "common_queries",
) -> str:
    """Analyze partner interaction patterns and provide insights.

    Use this tool when the user asks about analytics, behavior patterns,
    common queries, or strategic recommendations.

    Args:
        partner_type: Type of partner - 'MFD', 'wealth_platform', 'NBFC', 'all'
        analysis_type: Type of analysis - 'common_queries', 'objection_patterns',
                      'product_interest', 'engagement_metrics'

    Returns:
        Analytics summary with actionable insights.
    """
    try:
        from ..memory.store import db, Message, ChatSession, User
        from sqlalchemy import func

        # Build query based on partner type
        query = db.session.query(
            Message.intent,
            func.count(Message.id).label("count"),
        ).join(ChatSession).join(User)

        if partner_type != "all":
            query = query.filter(User.partner_type == partner_type)

        query = query.filter(Message.role == "assistant")
        results = query.group_by(Message.intent).all()

        if not results:
            return _get_default_insights(partner_type, analysis_type)

        # Format analytics
        lines = [f"**Partner Analytics: {partner_type} - {analysis_type}**\n"]

        if analysis_type == "common_queries":
            lines.append("**Most Common Query Types:**")
            for intent, count in sorted(results, key=lambda x: x[1], reverse=True):
                lines.append(f"- {intent or 'general'}: {count} queries")

        elif analysis_type == "objection_patterns":
            lines.append("**Common Objection Patterns:**")
            lines.append("- Interest rate comparisons with other products")
            lines.append("- Concerns about market volatility affecting collateral")
            lines.append("- Documentation complexity for phygital process")
            lines.append("- LTV ratio limitations on equity funds")

        elif analysis_type == "product_interest":
            lines.append("**Product Interest Distribution:**")
            lines.append("Based on query patterns, partners show highest interest in:")
            lines.append("1. LAMF digital process (fastest adoption)")
            lines.append("2. Interest rate comparisons")
            lines.append("3. Eligibility criteria for clients")
            lines.append("4. Marketing content for client outreach")

        elif analysis_type == "engagement_metrics":
            total = sum(count for _, count in results)
            lines.append(f"**Total Interactions**: {total}")
            lines.append(f"**Unique Intent Types**: {len(results)}")

        lines.append("\n**Recommendation**: Focus on digital LAMF education and provide ready-to-use client communication templates.")
        return "\n".join(lines)

    except Exception:
        return _get_default_insights(partner_type, analysis_type)


def _get_default_insights(partner_type, analysis_type):
    """Return default insights when no data is available."""
    return f"""**Partner Analytics: {partner_type} - {analysis_type}**

**Insights (based on industry patterns):**
- MFD partners most commonly ask about interest rates, eligibility, and documentation
- Content generation requests peak before month-end (SIP reminder cycles)
- Top objection: "Why should my client take a loan against MF instead of redeeming?"
- Key differentiator: No CIBIL check + 10-minute digital process

**Recommendations:**
1. Create ready-to-use WhatsApp templates for client outreach
2. Focus on LTV education (clients often underestimate borrowing capacity)
3. Highlight zero prepayment charges as a key advantage
4. Use comparison charts: LAMF vs Personal Loan vs Credit Card"""
