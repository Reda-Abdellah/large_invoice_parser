from langchain.prompts import PromptTemplate

def get_section_detail_prompt() -> PromptTemplate:
    return PromptTemplate(
            # input_variables=["section_content", "section_info", "parent_context"],
            input_variables=["item_info", "context_info", "item_content"],
            template= template_v2
        )

template_v2=template="""
            Analyze this specific offer item from a construction/engineering document and extract detailed specifications.
            Focus only on the item targeted by the item info.
            
            Item Info: {item_info}
            
            Context: {context_info}
            
            Item Content:
            {item_content}
            
            Extract detailed specifications for this construction item. Look for:
            - Quantities and units (m, m², m³, kg, pieces, hours)
            - Prices and costs
            - Technical specifications (DN sizes, diameters, materials)
            - Supplier information
            - Article/reference numbers
            - Material types and grades
            
            Return JSON format with detailed specifications:
            {{
                "item_details": {{
                    "supplier_id": "supplier_id_if_found",
                    "unit_quantity": number_or_null,
                    "unit_type": "MATERIAL|LABOR|SERVICE",
                    "percentage": number_or_0,
                    "unit": "m|m²|m³|kg|h|pcs|etc",
                    "unit_price": number_or_null,
                    "margin": number_or_25,
                    "auction_discount": number_or_0,
                    "supplier_discount_goal": number_or_0,
                    "billing_percent_situations": [],
                    "gantt_schedules": [],
                    "progress": number_or_0,
                    "employees_ids": [],
                    "article_id": "article_id_if_found",
                    "article_number": "article_number_if_found",
                    "desc_html": "<p>HTML formatted description</p>",
                    "is_ttc": false,
                    "taxes_rate_percent": number_or_0,
                    "apply_discount": false,
                    "isPageBreakBefore": false,
                    "isSellingPriceLocked": false,
                    "isInvalid": false,
                    "isCostPriceLocked": false,
                    "discount_value": number_or_0,
                    "is_optional": false,
                    "variants": [],
                    "articles": []
                }},
                "additional_fields": {{
                    "material_type": "material_if_specified",
                    "brand": "brand_if_specified",
                    "model": "model_if_specified",
                    "technical_specs": {{
                        "diameter": "DN_size_if_applicable",
                        "pressure": "pressure_rating_if_applicable",
                        "temperature": "temperature_rating_if_applicable",
                        "connection_type": "connection_type_if_applicable"
                    }},
                    "installation_notes": "installation_requirements_if_any"
                }},
                "extraction_metadata": {{
                    "found_quantity": true,
                    "found_price": false,
                    "found_technical_specs": true,
                    "confidence_level": "high|medium|low"
                }}
            }}
            
            EXTRACTION GUIDELINES:
            - If information is not available, use null for numbers, empty string for text, or "not_available"
            - Extract quantities from table cells or text (look for numbers followed by units)
            - Look for prices in currency format (€, EUR, Fr.)
            - Technical specs often in format "DN 100", "PN16", "∅ 3/4""
            - Material types like "acier", "laiton", "EPDM"
            - Brand names are often in tables with "Marque proposée"
            
            Focus on extracting precise numerical values and technical specifications.
            Return valid JSON only.
            """

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