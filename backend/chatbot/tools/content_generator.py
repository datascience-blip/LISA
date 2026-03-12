"""
Content Generator Tool for LISA AI
Generates marketing content for MFD partners
"""

from langchain_core.tools import tool


@tool
def generate_marketing_content(
    content_type: str,
    product: str = "LAMF",
    target_audience: str = "retail_investor",
    tone: str = "professional",
) -> str:
    """Generate marketing content for Lark Finserv financial products.

    Use this tool when the user explicitly asks you to create marketing materials
    like WhatsApp messages, emails, social media posts, or pitch scripts.

    Args:
        content_type: Type of content - 'whatsapp', 'email', 'social_media', 'pitch_script'
        product: Product name - 'LAMF', 'LAS', 'loan_against_shares'
        target_audience: Target audience - 'retail_investor', 'HNI', 'corporate'
        tone: Tone of content - 'professional', 'casual', 'educational'

    Returns:
        Generated marketing content text ready to use.
    """
    from config.config import Config
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    # Build the content generation prompt
    system = """You are a financial marketing content specialist for Lark Finserv.
Create compelling, compliant content for Loan Against Mutual Funds (LAMF) products.
Key product details to include when relevant:
- Interest rates from 10.5% per annum
- Processing fee: Rs. 999 + GST
- Loan tenure: Up to 36 months
- No prepayment charges
- Digital process: Complete in 10 minutes
- LTV: Up to 85% depending on fund type
- Min portfolio: Rs. 25,000
- No CIBIL check required
Always include a call-to-action."""

    prompt = f"""Create a {content_type} for {product} targeting {target_audience} in a {tone} tone.
Make it engaging, factual, and include relevant product details."""

    try:
        llm = ChatOpenAI(model=Config.LLM_MODEL, temperature=0.7, api_key=Config.OPENAI_API_KEY)
        response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"Content generation error: {str(e)}"
