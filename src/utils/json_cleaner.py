# src/utils/json_cleaner.py
import json
import re
from typing import Dict, Any, Optional

class JSONResponseCleaner:
    def __init__(self):
        self.json_patterns = [
            # Pattern 1: JSON wrapped in ```
            r'```json\s*(\{.*?\})\s*```',
            # Pattern 2: JSON wrapped in ``` blocks
            r'```\s*(\{.*?\})\s*```',
            # Pattern 3: JSON after <think> tags
            r'</think>\s*(\{.*?\})',
            # Pattern 4: Pure JSON (fallback)
            r'(\{.*?\})',
        ]
    
    def extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from LLM response"""
        if not response or not response.strip():
            return None
        
        # Remove <think> blocks entirely
        cleaned_response = self._remove_think_blocks(response)
        
        # Try to extract JSON using patterns
        for pattern in self.json_patterns:
            json_content = self._extract_with_pattern(cleaned_response, pattern)
            if json_content:
                return json_content
        
        # Last resort: try to find JSON-like content
        return self._extract_json_fallback(cleaned_response)
    
    def _remove_think_blocks(self, text: str) -> str:
        """Remove <think>...</think> blocks from text"""
        # Remove think blocks
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove other common wrapper tags
        text = re.sub(r'<analysis>.*?</analysis>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        return text.strip()
    
    def _extract_with_pattern(self, text: str, pattern: str) -> Optional[Dict[str, Any]]:
        """Extract JSON using a specific regex pattern"""
        try:
            # Compile pattern first to catch regex errors
            compiled_pattern = re.compile(pattern, re.DOTALL | re.IGNORECASE)
            matches = compiled_pattern.findall(text)
            
            for match in matches:
                # Clean the match
                json_str = match.strip()
                
                # Try to parse
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to fix common JSON issues
                    fixed_json = self._fix_common_json_issues(json_str)
                    if fixed_json:
                        try:
                            return json.loads(fixed_json)
                        except json.JSONDecodeError:
                            continue
            
            return None
            
        except re.error as e:
            print(f"Invalid regex pattern: {e}")
            return None
        except Exception as e:
            print(f"Pattern extraction error: {e}")
            return None
    
    def _fix_common_json_issues(self, json_str: str) -> Optional[str]:
        """Fix common JSON formatting issues"""
        try:
            # Remove trailing commas
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix unescaped quotes in strings - improved pattern
            json_str = re.sub(r'(?<!")(?<!\\)"(?![:,}\]])', '\\"', json_str)
            
            # Fix single quotes to double quotes (but be careful with contractions)
            json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
            
            # Fix missing quotes around keys
            json_str = re.sub(r'(\w+):', r'"\1":', json_str)
            
            # Fix boolean values
            json_str = re.sub(r'\bTrue\b', 'true', json_str)
            json_str = re.sub(r'\bFalse\b', 'false', json_str)
            json_str = re.sub(r'\bNone\b', 'null', json_str)
            
            return json_str
            
        except Exception:
            return None
    
    def _extract_json_fallback(self, text: str) -> Optional[Dict[str, Any]]:
        """Fallback method to extract JSON-like content"""
        try:
            # Look for the largest JSON-like block
            brace_count = 0
            start_pos = -1
            best_json = None
            
            for i, char in enumerate(text):
                if char == '{':
                    if brace_count == 0:
                        start_pos = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_pos != -1:
                        # Found a complete JSON block
                        json_candidate = text[start_pos:i+1]
                        try:
                            parsed = json.loads(json_candidate)
                            if isinstance(parsed, dict) and len(parsed) > 0:
                                best_json = parsed
                        except json.JSONDecodeError:
                            # Try to fix and parse
                            fixed = self._fix_common_json_issues(json_candidate)
                            if fixed:
                                try:
                                    parsed = json.loads(fixed)
                                    if isinstance(parsed, dict) and len(parsed) > 0:
                                        best_json = parsed
                                except json.JSONDecodeError:
                                    pass
            
            return best_json
            
        except Exception:
            return None
