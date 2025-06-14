

from langchain.prompts import PromptTemplate

def get_structure_prompt() -> PromptTemplate:
    return PromptTemplate(
            input_variables=["chunk_content", "chunk_info"],
            template= template_v3
        )

template_v3="""
            Analyze this construction/engineering offer markdown chunk and identify meaningful structural sections.
    
            Chunk Info: {chunk_info}
            
            Content:
            {chunk_content}
            
            IMPORTANT GUIDELINES:
            1. IGNORE: References, header, or footers that may be contained in the markdown
            2. IGNORE: Summary lines
            3. FOCUS ON: Actual work sections, technical specifications, and item categories
            
            Section Level Rules:
            - Level 1: Main work categories
            - Level 2: Sub-categories
            - Level 3: Detailed items
            
            Section Type Classification:
            - work_category: Main work divisions (CFC codes, trade sections)
            - materials: Pipes, tubes, equipment specifications
            - accessories: Valves, fittings, measuring devices
            - technical_specs: Tables with dimensions, pressures, temperatures
            - pricing: Cost-related information
            
            For each MEANINGFUL section, provide:
            - Precise start delimiter (exact text that begins the section)
            - Precise end delimiter (text that ends the section, or next section start)
            - Coherent title that represents the actual work/content
            
            Return JSON format:
            {{
                "sections": [
                    {{
                        "section_id": "unique_id",
                        "title": "clean section title without formatting marks",
                        "level": 1|2|3,
                        "section_type": "work_category|materials|accessories|technical_specs|pricing",
                        "start_delimiter": "exact text that starts this section",
                        "end_delimiter": "exact text that ends this section or starts next section",
                        "estimated_content": "what this section contains (items, specifications, etc.)",
                        "has_items": true,
                        "item_count_estimate": 5
                    }}
                ]
            }}
            
            Be precise with delimiters and ensure they can be reliably found in the markdown.
            Focus on sections that contain actual work items, not administrative text.
            """

template_v2="""
            Analyze this construction/engineering offer markdown chunk and identify meaningful structural sections.
    
            Chunk Info: {chunk_info}
            
            Content:
            {chunk_content}
            
            IMPORTANT GUIDELINES:
            1. IGNORE: Image references like ![](_page_X_Picture_Y.jpeg)
            2. IGNORE: Summary lines like "TOTAL 243. A. 1. Tuyauteries Fr. ..................."
            3. IGNORE: Report lines like "A reporter Fr. ................."
            4. FOCUS ON: Actual work sections, technical specifications, and item categories
            
            Section Level Rules:
            - Level 1: Main work categories (e.g., "243. A. DISTRIBUTION DE CHALEUR ACTIVITES")
            - Level 2: Sub-categories (e.g., "243. A. 1. Tuyauteries", "243. A. 2. Accessoires")
            - Level 3: Detailed items (e.g., "1. Circuit eau normale", "2. Vanne d'arrêt")
            
            Section Type Classification:
            - work_category: Main work divisions (CFC codes, trade sections)
            - materials: Pipes, tubes, equipment specifications
            - accessories: Valves, fittings, measuring devices
            - technical_specs: Tables with dimensions, pressures, temperatures
            - pricing: Cost-related information
            
            For each MEANINGFUL section, provide:
            - Precise start delimiter (exact text that begins the section)
            - Precise end delimiter (text that ends the section, or next section start)
            - Coherent title that represents the actual work/content
            
            Return JSON format:
            {{
                "sections": [
                    {{
                        "section_id": "unique_id",
                        "title": "clean section title without formatting marks",
                        "level": 1,
                        "section_type": "work_category|materials|accessories|technical_specs|pricing",
                        "start_delimiter": "exact text that starts this section",
                        "end_delimiter": "exact text that ends this section or starts next section",
                        "estimated_content": "what this section contains (items, specifications, etc.)",
                        "has_items": true,
                        "item_count_estimate": 5
                    }}
                ]
            }}
            
            EXAMPLE STRUCTURE FOR GIVEN CONTENT:
            - Main section: "DISTRIBUTION DE CHALEUR ACTIVITES" (level 1, work_category)
            - Sub-section: "Tuyauteries" (level 2, materials) 
            - Detail section: "Circuit eau normale, Réseaux intérieurs" (level 3, technical_specs)
            - Sub-section: "Accessoires" (level 2, accessories)
            - Detail items: "Compteur de chaleur", "Vanne d'arrêt", etc. (level 3, accessories)
            
            Be precise with delimiters and ensure they can be reliably found in the markdown.
            Focus on sections that contain actual work items, not administrative text.
            """

template_v1="""
            Analyze this construction/engineering offer markdown chunk and identify meaningful structural sections.
    
            Chunk Info: {chunk_info}
            
            Content:
            {chunk_content}
            
            IMPORTANT GUIDELINES:
            1. IGNORE: Image references like ![](_page_X_Picture_Y.jpeg)
            2. IGNORE: Summary lines like "TOTAL 243. A. 1. Tuyauteries Fr. ..................."
            3. IGNORE: Report lines like "A reporter Fr. ................."
            4. FOCUS ON: Actual work sections, technical specifications, and item categories
            
            Section Level Rules:
            - Level 1: Main work categories (e.g., "243. A. DISTRIBUTION DE CHALEUR ACTIVITES")
            - Level 2: Sub-categories (e.g., "243. A. 1. Tuyauteries", "243. A. 2. Accessoires")
            - Level 3: Detailed items (e.g., "1. Circuit eau normale", "2. Vanne d'arrêt")
            
            Section Type Classification:
            - work_category: Main work divisions (CFC codes, trade sections)
            - materials: Pipes, tubes, equipment specifications
            - accessories: Valves, fittings, measuring devices
            - technical_specs: Tables with dimensions, pressures, temperatures
            - pricing: Cost-related information
            
            For each MEANINGFUL section, provide:
            - Precise start delimiter (exact text that begins the section)
            - Precise end delimiter (text that ends the section, or next section start)
            - Coherent title that represents the actual work/content
            
            Return JSON format:
            {{
                "sections": [
                    {{
                        "section_id": "unique_id",
                        "title": "clean section title without formatting marks",
                        "level": 1,
                        "section_type": "work_category|materials|accessories|technical_specs|pricing",
                        "start_delimiter": "exact text that starts this section",
                        "end_delimiter": "exact text that ends this section or starts next section",
                        "estimated_content": "what this section contains (items, specifications, etc.)",
                        "has_items": true,
                        "item_count_estimate": 5
                    }}
                ]
            }}
            
            EXAMPLE STRUCTURE FOR GIVEN CONTENT:
            - Main section: "DISTRIBUTION DE CHALEUR ACTIVITES" (level 1, work_category)
            - Sub-section: "Tuyauteries" (level 2, materials) 
            - Detail section: "Circuit eau normale, Réseaux intérieurs" (level 3, technical_specs)
            - Sub-section: "Accessoires" (level 2, accessories)
            - Detail items: "Compteur de chaleur", "Vanne d'arrêt", etc. (level 3, accessories)
            
            Be precise with delimiters and ensure they can be reliably found in the markdown.
            Focus on sections that contain actual work items, not administrative text.
            """