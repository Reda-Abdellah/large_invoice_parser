from langchain.prompts import PromptTemplate

def get_consolidation_prompt() -> PromptTemplate:
    return PromptTemplate(
            input_variables=["chunk_content", "chunk_info"],
            template= template_v3
        )

template_v3="""
            Consolidate these section analyses from multiple overlapping chunks into a coherent construction offer structure.
            Remove duplicates, merge overlapping sections, and create a logical hierarchy.
            The sections are ordered by their appearance in the document, so maintain that order in the output and joint the parts if needed.
            
            Sections from all chunks:
            {all_sections}
            
            HIERARCHY LOGIC:
            - Level 1: Main work categories
            - Level 2: Work sub-categories  
            - Level 3: Specific items or technical details
            
            CONSOLIDATION RULES:
            1. Merge consecutive sections with similar titles (e.g., "Tuyauteries" from different chunks)
            2. Maintain proper hierarchy: work_category > materials/accessories > technical_specs
            3. Remove administrative sections (totals, reports, image references)
            4. Ensure parent-child relationships make sense
            5. Combine item estimates for merged sections
            
            
            Return consolidated structure in JSON format.
            
            Focus on creating a clean, logical structure that represents the actual construction work breakdown.
            """


template_v2="""
            Consolidate these section analyses from multiple chunks into a coherent construction offer structure.
            Remove duplicates, merge overlapping sections, and create a logical hierarchy.
            
            Sections from all chunks:
            {all_sections}
            
            CONSOLIDATION RULES:
            1. Merge sections with similar titles (e.g., "Tuyauteries" from different chunks)
            2. Maintain proper hierarchy: work_category > materials/accessories > technical_specs
            3. Remove administrative sections (totals, reports, image references)
            4. Ensure parent-child relationships make sense
            5. Combine item estimates for merged sections
            
            HIERARCHY LOGIC:
            - Level 1: Main work categories (CFC codes like "243. A. DISTRIBUTION DE CHALEUR")
            - Level 2: Work sub-categories ("Tuyauteries", "Accessoires")  
            - Level 3: Specific items or technical details
            
            Return consolidated structure in JSON format:
            {{
                "document_structure": {{
                    "total_sections": 8,
                    "main_categories": ["work_category", "materials", "accessories"],
                    "estimated_total_items": 25,
                    "sections": [
                        {{
                            "section_id": "unique_id",
                            "title": "clean consolidated title",
                            "level": 1,
                            "section_type": "work_category|materials|accessories|technical_specs",
                            "start_delimiter": "exact start text",
                            "end_delimiter": "exact end text",
                            "estimated_content": "consolidated description",
                            "parent_section_id": null,
                            "child_sections": ["child_id_1", "child_id_2"],
                            "has_items": true,
                            "item_count_estimate": 10,
                            "merged_from_chunks": ["chunk_1", "chunk_2"]
                        }}
                    ]
                }}
            }}
            
            Focus on creating a clean, logical structure that represents the actual construction work breakdown.
            """

template_v1="""
            Consolidate these section analyses from multiple chunks into a coherent construction offer structure.
            Remove duplicates, merge overlapping sections, and create a logical hierarchy.
            
            Sections from all chunks:
            {all_sections}
            
            CONSOLIDATION RULES:
            1. Merge sections with similar titles (e.g., "Tuyauteries" from different chunks)
            2. Maintain proper hierarchy: work_category > materials/accessories > technical_specs
            3. Remove administrative sections (totals, reports, image references)
            4. Ensure parent-child relationships make sense
            5. Combine item estimates for merged sections
            
            HIERARCHY LOGIC:
            - Level 1: Main work categories (CFC codes like "243. A. DISTRIBUTION DE CHALEUR")
            - Level 2: Work sub-categories ("Tuyauteries", "Accessoires")  
            - Level 3: Specific items or technical details
            
            Return consolidated structure in JSON format:
            {{
                "document_structure": {{
                    "total_sections": 8,
                    "main_categories": ["work_category", "materials", "accessories"],
                    "estimated_total_items": 25,
                    "sections": [
                        {{
                            "section_id": "unique_id",
                            "title": "clean consolidated title",
                            "level": 1,
                            "section_type": "work_category|materials|accessories|technical_specs",
                            "start_delimiter": "exact start text",
                            "end_delimiter": "exact end text",
                            "estimated_content": "consolidated description",
                            "parent_section_id": null,
                            "child_sections": ["child_id_1", "child_id_2"],
                            "has_items": true,
                            "item_count_estimate": 10,
                            "merged_from_chunks": ["chunk_1", "chunk_2"]
                        }}
                    ]
                }}
            }}
            
            Focus on creating a clean, logical structure that represents the actual construction work breakdown.
            """