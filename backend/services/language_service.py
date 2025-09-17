from langdetect import detect, DetectorFactory, LangDetectException
from typing import Dict, Optional, Tuple
import re

# Set seed for consistent results
DetectorFactory.seed = 0

class LanguageService:
    def __init__(self):
        # Common greetings and phrases in different languages
        self.language_patterns = {
            'rw': {  # Kinyarwanda
                'greetings': ['mwiriwe', 'muraho', 'bite', 'amakuru', 'mwaramutse'],
                'responses': {
                    'greeting': 'Mwiriwe! Ndashaka kugufasha. Ushobora kubaza ibibazo bijyanye n\'inyandiko cyangwa ibindi.',
                    'help': 'Ndashaka kugufasha. Ushobora kubaza ibibazo bijyanye n\'inyandiko cyangwa ibindi.',
                    'error': 'Ihangane, habaye ikosa. Ongera ugerageze.',
                    'processing': 'Ndimo gukora...'
                }
            },
            'fr': {  # French
                'greetings': ['bonjour', 'salut', 'bonsoir', 'comment allez-vous'],
                'responses': {
                    'greeting': 'Bonjour! Je suis là pour vous aider. Vous pouvez me poser des questions sur les documents ou autres sujets.',
                    'help': 'Je peux vous aider avec des questions sur les documents ou des sujets généraux.',
                    'error': 'Désolé, il y a eu une erreur. Veuillez réessayer.',
                    'processing': 'Traitement en cours...'
                }
            },
            'sw': {  # Swahili
                'greetings': ['hujambo', 'habari', 'mambo', 'salamu'],
                'responses': {
                    'greeting': 'Hujambo! Niko hapa kukusaidia. Unaweza kuuliza maswali kuhusu hati au mada nyingine.',
                    'help': 'Ninaweza kukusaidia na maswali kuhusu hati au mada za jumla.',
                    'error': 'Samahani, kumekuwa na hitilafu. Tafadhali jaribu tena.',
                    'processing': 'Inachakata...'
                }
            },
            'en': {  # English
                'greetings': ['hello', 'hi', 'hey', 'good morning', 'good evening'],
                'responses': {
                    'greeting': 'Hello! I\'m here to help you. You can ask questions about documents or other topics.',
                    'help': 'I can help you with questions about documents or general topics.',
                    'error': 'Sorry, there was an error. Please try again.',
                    'processing': 'Processing...'
                }
            }
        }
        
        # Language names for user-friendly display
        self.language_names = {
            'rw': 'Kinyarwanda',
            'fr': 'Français',
            'sw': 'Kiswahili', 
            'en': 'English',
            'es': 'Español',
            'de': 'Deutsch',
            'it': 'Italiano',
            'pt': 'Português'
        }
    
    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language of input text
        Returns: (language_code, confidence)
        """
        if not text or not text.strip():
            return 'en', 0.5
        
        text_clean = text.lower().strip()
        
        # First check for known patterns/greetings
        for lang_code, patterns in self.language_patterns.items():
            for greeting in patterns['greetings']:
                if greeting in text_clean:
                    return lang_code, 0.9
        
        # Use langdetect for general detection
        try:
            detected_lang = detect(text)
            confidence = 0.8  # langdetect doesn't provide confidence, so we estimate
            
            # Map some common language codes
            lang_mapping = {
                'rw': 'rw',  # Kinyarwanda
                'fr': 'fr',  # French
                'sw': 'sw',  # Swahili
                'en': 'en',  # English
                'es': 'es',  # Spanish
                'de': 'de',  # German
                'it': 'it',  # Italian
                'pt': 'pt'   # Portuguese
            }
            
            mapped_lang = lang_mapping.get(detected_lang, 'en')
            return mapped_lang, confidence
            
        except LangDetectException:
            # Fallback to English if detection fails
            return 'en', 0.3
    
    def is_greeting(self, text: str, language: str = None) -> bool:
        """Check if text is a greeting"""
        text_clean = text.lower().strip()
        
        if language and language in self.language_patterns:
            return any(greeting in text_clean for greeting in self.language_patterns[language]['greetings'])
        
        # Check all languages if language not specified
        for patterns in self.language_patterns.values():
            if any(greeting in text_clean for greeting in patterns['greetings']):
                return True
        
        return False
    
    def get_localized_response(self, response_type: str, language: str) -> str:
        """Get a localized response for common scenarios"""
        if language in self.language_patterns:
            return self.language_patterns[language]['responses'].get(response_type, '')
        return self.language_patterns['en']['responses'].get(response_type, '')
    
    def create_multilingual_prompt(self, base_prompt: str, detected_language: str, confidence: float) -> str:
        """Create a language-aware system prompt"""
        
        language_name = self.language_names.get(detected_language, detected_language)
        
        if confidence > 0.7:
            language_instruction = f"""
IMPORTANT LANGUAGE INSTRUCTION:
- The user is communicating in {language_name} ({detected_language})
- You MUST respond in the same language ({language_name})
- Maintain the same language throughout the conversation
- If you're unsure about a translation, ask for clarification in {language_name}
"""
        else:
            language_instruction = f"""
LANGUAGE INSTRUCTION:
- The user's language appears to be {language_name} ({detected_language}) but I'm not completely certain
- Try to respond in {language_name} if possible
- If the language seems unclear, politely ask which language the user prefers
- Supported languages: English, Français, Kinyarwanda, Kiswahili
"""
        
        return f"{base_prompt}\n{language_instruction}"
    
    def handle_greeting(self, text: str, language: str, organization_name: str = None) -> str:
        """Handle greeting messages with appropriate localized response"""
        base_response = self.get_localized_response('greeting', language)
        
        if organization_name:
            if language == 'rw':
                return f"{base_response}\n\nUri muri {organization_name}. Ushobora kubaza ibibazo bijyanye n'inyandiko zacu."
            elif language == 'fr':
                return f"{base_response}\n\nVous êtes dans {organization_name}. Vous pouvez poser des questions sur nos documents."
            elif language == 'sw':
                return f"{base_response}\n\nUko katika {organization_name}. Unaweza kuuliza maswali kuhusu hati zetu."
            else:  # English
                return f"{base_response}\n\nYou're in {organization_name}. You can ask questions about our documents."
        
        return base_response
    
    def get_language_options_message(self) -> Dict[str, str]:
        """Get language selection message in multiple languages"""
        return {
            'en': "I detected multiple possible languages. Which language would you prefer?\n• English\n• Français\n• Kinyarwanda\n• Kiswahili",
            'fr': "J'ai détecté plusieurs langues possibles. Quelle langue préférez-vous?\n• English\n• Français\n• Kinyarwanda\n• Kiswahili",
            'rw': "Nabonye indimi nyinshi zishoboka. Ni iyihe ndimi ushaka?\n• English\n• Français\n• Kinyarwanda\n• Kiswahili",
            'sw': "Nimebaini lugha nyingi zinazowezekana. Ungependa lugha gani?\n• English\n• Français\n• Kinyarwanda\n• Kiswahili"
        }
    
    def translate_error_message(self, error_msg: str, target_language: str) -> str:
        """Translate error messages to target language"""
        return self.get_localized_response('error', target_language) or error_msg