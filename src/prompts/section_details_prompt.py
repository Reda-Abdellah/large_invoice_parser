from langchain.prompts import PromptTemplate

def get_section_detail_prompt() -> PromptTemplate:
    return PromptTemplate(
            input_variables=["section_content", "section_info", "parent_context"],
            template= template_v1
        )


template_v1="""
            Analyze this specific detailed section from a construction/engineering offer and extract offer items.
            
            Section Info: {section_info}
            
            Parent Context: {parent_context}
            
            Section Content:
            {section_content}
            
            IMPORTANT: This is a level 3 detailed section. Extract individual offer items with precise specifications.
            
            Return JSON format:
            {{
                "section_analysis": {{
                    "section_id": "section_id",
                    "section_title": "title",
                    "section_type": "materials|accessories|technical_specs|pricing",
                    "group_type": "SUB",
                    "default_margin": 25,
                    "parent_section_id": "parent_id"
                }},
                "offer_items": [
                    {{
                        "name": "detailed item description",
                        "offer_item_type": "NORMAL",
                        "unit_quantity": 10,
                        "unit_type": "MATERIAL",
                        "unit": "m",
                        "unit_price": 15.50,
                        "margin": 25,
                        "article_number": "ref123",
                        "desc_html": "<p>HTML description</p>",
                        "is_optional": false,
                        "category": "item category"
                    }}
                ],
                "section_metadata": {{
                    "total_items": 1,
                    "has_pricing": true,
                    "has_quantities": true,
                    "technical_specs": ["spec1", "spec2"],
                    "key_materials": ["material1", "material2"]
                }}
            }}
            
            Focus on extracting individual items with quantities, units, and specifications.
            Return valid JSON only.
            """