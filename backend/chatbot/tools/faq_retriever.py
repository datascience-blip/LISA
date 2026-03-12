"""
FAQ Retriever Tool for LISA AI
Direct FAQ lookup with structured responses
"""

from langchain_core.tools import tool

# Pre-built FAQ database for instant, accurate responses
FAQ_DATABASE = {
    "interest_rates": {
        "question": "What are the interest rates for LAMF?",
        "answer": """**Interest Rates for Loan Against Mutual Funds (LAMF):**
- Starting from **10.5% per annum**
- Rates vary by lender partner:
  - BFL (Bajaj Finance): Competitive digital rates
  - DSP Finance: Digital processing rates
  - ABFL (Aditya Birla Finance): Phygital process rates
  - Tata Capital: Phygital process rates
- Rate depends on fund type, loan amount, and tenure
- *Terms may vary by lender. Contact Lark Finserv for exact rates.*""",
    },
    "eligibility": {
        "question": "Who is eligible for LAMF?",
        "answer": """**Eligibility Criteria for LAMF:**
- **Age**: 18 to 69 years
- **Minimum Portfolio**: Rs. 25,000 in mutual funds
- **No CIBIL check** required
- **Entity types**: Individual, HUF, Partnership, LLP, Company
- **Resident Indian** citizens
- Mutual funds must be in approved list of lender
- *Specific eligibility may vary by lender partner.*""",
    },
    "documents_required": {
        "question": "What documents are needed for LAMF?",
        "answer": """**Documents Required for LAMF:**
- **Digital Process** (BFL, DSP):
  - PAN Card
  - Aadhaar Card
  - Bank account details
  - Mutual fund portfolio details (via CAS/CAMS)
- **Phygital Process** (ABFL, Tata Capital):
  - KYC documents (PAN + Aadhaar)
  - Signed application form
  - Bank statements (if required)
  - Physical pledge documents""",
    },
    "process": {
        "question": "How does the LAMF application process work?",
        "answer": """**LAMF Application Process:**
1. **Digital (BFL/DSP)** - Complete in ~10 minutes:
   - Submit online application
   - e-KYC verification
   - Select mutual fund units to pledge
   - e-Sign documents
   - Loan disbursed to bank account
2. **Phygital (ABFL/Tata Capital)** - 7-10 business days:
   - Submit application with documents
   - Physical verification
   - Pledge mutual fund units
   - Sign physical documents
   - Loan disbursed after verification""",
    },
    "prepayment": {
        "question": "Are there prepayment charges?",
        "answer": """**Prepayment Policy:**
- **No prepayment charges** on LAMF
- You can repay the loan partially or fully at any time
- No lock-in period
- Interest charged only for the period of borrowing
- *This is one of the key advantages of LAMF over traditional loans.*""",
    },
    "loan_to_value": {
        "question": "What is the Loan-to-Value (LTV) ratio?",
        "answer": """**Loan-to-Value (LTV) Ratios:**
- **Equity Mutual Funds**: Up to 50% LTV
- **Debt/Hybrid Mutual Funds**: Up to 80-85% LTV
- **Liquid/Money Market Funds**: Up to 85-90% LTV
- **Shares (Listed)**: Up to 50% LTV
- LTV depends on the type of security and lender
- *Higher LTV means you can borrow more against your portfolio.*""",
    },
    "tenure": {
        "question": "What is the loan tenure?",
        "answer": """**Loan Tenure:**
- **Minimum**: 6 months (varies by lender)
- **Maximum**: Up to 36 months
- Flexible repayment options
- Overdraft facility available (borrow as needed)
- Renewal possible at end of tenure
- *Tenure options may vary by lender partner.*""",
    },
    "fees": {
        "question": "What are the fees and charges?",
        "answer": """**Fees & Charges for LAMF:**
- **Processing Fee**: Rs. 999 + GST (one-time)
- **Stamp Duty**: As applicable
- **Prepayment Charges**: NIL
- **Late Payment**: Interest penalty may apply
- **Renewal Fee**: Applicable at tenure end
- **No hidden charges**
- *Fee structure may vary slightly by lender partner.*""",
    },
}


@tool
def lookup_faq(question_topic: str) -> str:
    """Look up frequently asked questions about LAMF/LAS products.

    Use this tool for direct, factual answers about standard product details
    like rates, eligibility, fees, process, etc.

    Args:
        question_topic: The FAQ topic - 'interest_rates', 'eligibility',
                       'documents_required', 'process', 'prepayment',
                       'loan_to_value', 'tenure', 'fees'

    Returns:
        Structured FAQ answer with specific numbers and details.
    """
    topic = question_topic.lower().strip()
    faq = FAQ_DATABASE.get(topic)

    if faq:
        return faq["answer"]

    # Fuzzy match
    for key, value in FAQ_DATABASE.items():
        if topic in key or key in topic:
            return value["answer"]

    available = ", ".join(FAQ_DATABASE.keys())
    return f"FAQ topic '{topic}' not found. Available topics: {available}"
