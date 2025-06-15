

from langchain.prompts import PromptTemplate

def get_structure_prompt() -> PromptTemplate:
    return PromptTemplate(
            # input_variables=["chunk_content", "chunk_info"],
            input_variables=["chunk_info", "chunk_content", "previous_output"],
            template= template_v5
        )

template_v5 = """
            Extract offer items from this construction/engineering document chunk, maintaining hierarchical structure and avoiding duplicates.

            Chunk Info: {chunk_info}

            Previous Context (from earlier chunks):
            {previous_context}

            Content:
            {chunk_content}

            IMPORTANT - CHUNK OVERLAP HANDLING:
            - These chunks are processed sequentially with overlapping content
            - DO NOT repeat items that were already extracted in previous chunks
            - If you see an item that appears in the previous context, SKIP it
            - If an item appears to continue from previous chunks (same specifications, similar content), only extract the NEW parts

            CONTINUITY RULES:
            - If no clear main category (# header) is found in this chunk, assume items belong to the LAST main category from previous context
            - If no clear sub-category (#### header) is found, assume items belong to the LAST sub-category from previous context
            - Items without explicit grouping likely continue the current hierarchy from previous chunks

            EXTRACTION RULES:
            1. IGNORE: Image references, totals, summary lines, page headers/footers
            2. IGNORE: Items already mentioned in previous context
            3. IDENTIFY: NEW main categories (# headers like "243. A. DISTRIBUTION DE CHALEUR ACTIVITES")
            4. IDENTIFY: NEW sub-categories (#### headers like "243. A. 1. Tuyauteries", "243. A. 2. Accessoires")
            5. EXTRACT: Only NEW individual offer items from tables, lists, and descriptions

            ITEM IDENTIFICATION:
            - Table rows with specifications (DN sizes, diameters, quantities)
            - Numbered items (1. Compteur de chaleur, 2. Vanne d'arrêt)
            - Equipment descriptions with technical specs
            - Material specifications with quantities and units
            - Continuation of specifications from previous chunks (only NEW information)

            HIERARCHY INFERENCE:
            - If this chunk has items but no group headers, use the last active group from previous context
            - If this chunk starts mid-specification, it likely continues the last item category
            - Look for contextual clues like "suite" (continuation), numbering sequences, or similar technical patterns

            For each NEW offer item, provide:
            - Exact start and end delimiters for precise text extraction
            - Clean item name/description
            - Parent hierarchy (main category → sub-category → item)
            - Indicate if this item continues a previous category

            Return JSON format:
            {{
                "offer_item_groups": [
                    {{
                        "name": "Main Category Name (only if NEW or different from previous)",
                        "group_type": "BASE",
                        "is_continuation": false,
                        "offer_groups": [
                            {{
                                "name": "Sub Category Name (only if NEW or different from previous)", 
                                "group_type": "SUB",
                                "is_continuation": false,
                                "offer_items": [
                                    {{
                                        "name": "Item description",
                                        "start_delimiter": "exact text that starts this item",
                                        "end_delimiter": "exact text that ends this item",
                                        "chunk_id": "current_chunk_id",
                                        "estimated_content": "brief description of item specs",
                                    }}
                                ]
                            }}
                        ]
                    }}
                ],

            }}

            EXAMPLES from the content:
            - Main: "DISTRIBUTION DE CHALEUR ACTIVITES" (BASE group)
            - Sub: "Tuyauteries" (SUB group)  
            - Items: "DN 100", "DN 80", "DN 65", etc. (individual offer items)
            - Sub: "Accessoires" (SUB group)
            - Items: "Compteur de chaleur", "Vanne d'arrêt", etc.

            OVERLAP EXAMPLE:
            - If previous chunk ended with "DN 80" and this chunk starts with "DN 80" followed by "DN 65", only extract "DN 65"
            - If previous chunk had "Compteur de chaleur" and this chunk shows the same item with additional specs, only extract the NEW specifications

            Focus on extracting only NEW purchasable/billable items with their context.
            Be precise with delimiters and avoid any duplication from previous chunks.
            When in doubt about hierarchy, use the last known group structure from previous context.
            """
template_v4 = """
            Analyze this construction/engineering offer markdown chunk and identify meaningful structural sections.
            Use the previous structural analysis to maintain continuity and proper section numbering.
            
            Chunk Info: {chunk_info}
            
            Content:
            {chunk_content}
            
            Previous sections from earlier chunks:
            {previous_output}
            
            IMPORTANT GUIDELINES:
            1. IGNORE: Image references, headers, footers, page numbers
            2. IGNORE: Summary lines like "TOTAL X.X.X Fr. ..................."
            3. IGNORE: Report lines like "A reporter Fr. ................."
            4. FOCUS ON: Actual work sections, technical specifications, and item categories
            5. MAINTAIN CONTINUITY: Use previous section IDs to continue numbering logically
            
            Section Level Rules & ID Format:
            - Level 1 (Main work categories): section_id = (e.g., "1", "2", "3", etc.)
            - Level 2 (Sub-categories): section_id = (e.g., "1.1", "1.2", "2.1", etc.)
            - Level 3 (Detailed items): section_id = (e.g., "1.1.1", "1.2.2", "2.1.1", etc.)
            For instance section_id = X.Y.Z means it is a level 3 structure child of level 2 section Y and level 1 section X.
            section_id should be unique across the document and should be incremental based on level.
            
            NUMBERING LOGIC:
            - If this chunk continues a section from previous chunks, use the next logical ID
            - If this chunk starts a new main category, increment the main ID
            - Don't confuse markdown numbering (like "1. Circuit eau normale") with section_id
            - The section_id tracks the document structure, not the markdown formatting
            
            For each MEANINGFUL section, provide:
            - Hierarchical section_id following the X.Y.Z format
            - Clean title from the markdown (keep it in the same language as the chunk) 
            - Precise delimiters for exact text extraction
            
            Return JSON format:
            {{
                "sections": [
                    {{
                        "section_id": "X.Y.Z",  # Unique ID for this section
                        "title": "clean section title without formatting marks",
                        "level": 1|2|3,
                        "section_type": "work_category|materials|accessories|technical_specs|pricing",
                        "start_delimiter": "exact text that starts this section",
                        "end_delimiter": "exact text that ends this section or starts next section",
                        "estimated_content": "what this section contains (items, specifications, etc.)",
                        "parent_section_id": "1.2",
                        "continues_from_previous": false,
                    }}
                ]
            }}
            
            EXAMPLES:
            - If previous chunk ended with section "1.2", and this chunk has items in that category, use "1.2.1", "1.2.2"
            - If this chunk starts a completely new main category, use "2" (next main ID)
            - If continuing sub-category "1.1" from previous chunk, next items would be "1.1.3", "1.1.4", etc.
            
            Be precise with delimiters and focus on actual work content, not formatting artifacts.
            """

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