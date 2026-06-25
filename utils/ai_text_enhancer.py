"""AI Text Enhancer - Rephrases and enhances cause/resolution text."""

from typing import Optional
import os
import re
from openai import OpenAI


class AITextEnhancer:
    """Enhances and rephrases technical text using AI."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize AI Text Enhancer.
        
        Args:
            model: OpenAI model to use
        """
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def enhance_cause(self, cause_text: str) -> str:
        """Enhance and rephrase cause text to be short and sweet.
        
        Args:
            cause_text: Raw cause text from Git issue
            
        Returns:
            Enhanced cause text (short and concise paragraph)
        """
        if not cause_text or len(cause_text.strip()) < 10:
            return cause_text
        
        prompt = f"""Convert this into a SINGLE FLOWING PARAGRAPH. No bullet points, no numbered lists, no line breaks between sentences. Just one continuous paragraph.

{cause_text}

Paragraph (2-3 sentences, flowing text):"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You write clear, flowing paragraphs. You NEVER use bullet points or numbered lists. You always write in continuous prose."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            content = response.choices[0].message.content
            if not content:
                return cause_text
            
            # Post-process to remove any lists
            enhanced = self._convert_to_paragraph(content.strip())
            return enhanced
            
        except Exception as e:
            print(f"Error enhancing cause text: {e}")
            return cause_text
    
    def enhance_resolution(self, resolution_text: str) -> str:
        """Enhance and rephrase resolution text to be short and sweet.
        
        Args:
            resolution_text: Raw resolution text from Git issue
            
        Returns:
            Enhanced resolution text (short and actionable paragraph)
        """
        if not resolution_text or len(resolution_text.strip()) < 10:
            return resolution_text
        
        prompt = f"""Convert this into a SINGLE FLOWING PARAGRAPH. No bullet points, no numbered lists, no line breaks between sentences. Just one continuous paragraph describing the steps.

{resolution_text}

Paragraph (3-4 sentences, flowing text):"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You write clear, flowing paragraphs. You NEVER use bullet points or numbered lists. You always write in continuous prose."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            content = response.choices[0].message.content
            if not content:
                return resolution_text
            
            # Post-process to remove any lists
            enhanced = self._convert_to_paragraph(content.strip())
            return enhanced
            
        except Exception as e:
            print(f"Error enhancing resolution text: {e}")
            return resolution_text
    
    def _convert_to_paragraph(self, text: str) -> str:
        """Convert any list format to a flowing paragraph.
        
        Args:
            text: Text that might contain lists
            
        Returns:
            Flowing paragraph text
        """
        # Remove numbered lists (1. 2. 3. etc.)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Remove bullet points (- * •)
        text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)
        
        # Remove bold markers from list items
        text = re.sub(r'\*\*([^*]+)\*\*:', r'\1 -', text)
        
        # Join lines into a single paragraph
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        paragraph = ' '.join(lines)
        
        # Clean up multiple spaces
        paragraph = re.sub(r'\s+', ' ', paragraph)
        
        return paragraph.strip()
    
    def enhance_both(self, cause_text: Optional[str], resolution_text: Optional[str]) -> dict:
        """Enhance both cause and resolution text.
        
        Args:
            cause_text: Raw cause text
            resolution_text: Raw resolution text
            
        Returns:
            Dict with enhanced_cause and enhanced_resolution
        """
        result: dict[str, Optional[str]] = {
            "enhanced_cause": None,
            "enhanced_resolution": None
        }
        
        if cause_text:
            result["enhanced_cause"] = self.enhance_cause(cause_text)
        
        if resolution_text:
            result["enhanced_resolution"] = self.enhance_resolution(resolution_text)
        
        return result


# Singleton instance
_enhancer_instance = None


def get_ai_text_enhancer() -> AITextEnhancer:
    """Get singleton instance of AITextEnhancer.
    
    Returns:
        AITextEnhancer: Singleton instance
    """
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = AITextEnhancer()
    return _enhancer_instance


# Made with Bob