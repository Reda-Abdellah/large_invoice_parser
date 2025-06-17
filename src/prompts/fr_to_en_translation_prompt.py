from langchain.prompts import PromptTemplate

fr_to_en_prompt = PromptTemplate(
    input_variables=["french_content"],
    template="""
    Translate this French construction/engineering document to English.
    Preserve the exact markdown structure, formatting, headers, and technical specifications.
    Keep technical terms, measurements, and reference numbers unchanged.
    
    IMPORTANT:
    - Maintain all markdown formatting (headers, tables, lists)
    - Keep technical specifications like "DN 100", "PN16", measurements in original form
    - Preserve reference numbers and codes (like "CFC 243.A")
    - Translate only descriptive text, not technical data
    
    French content:
    {french_content}
    
    Return the English translation maintaining exact formatting:
    """
)

en_to_fr_prompt = PromptTemplate(
    input_variables=["english_content", "original_french_terms"],
    template="""
    Translate this English construction/engineering content back to French.
    Use the original French technical terms and maintain professional construction terminology.
    
    Original French technical terms to preserve:
    {original_french_terms}
    
    English content to translate:
    {english_content}
    
    Return the French translation using proper construction terminology:
    """
)