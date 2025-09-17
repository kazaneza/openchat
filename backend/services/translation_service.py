from googletrans import Translator
from typing import Optional, Tuple, Dict
import traceback
from .language_service import LanguageService

class TranslationService:
    def __init__(self):
        self.translator = Translator()
        self.language_service = LanguageService()
        
        # Language code mapping for Google Translate
        self.lang_mapping = {
            'rw': 'rw',  # Kinyarwanda
            'fr': 'fr',  # French
            'sw': 'sw',  # Swahili
            'en': 'en',  # English
            'es': 'es',  # Spanish
            'de': 'de',  # German
            'it': 'it',  # Italian
            'pt': 'pt'   # Portuguese
        }
        
        # Cache for translations to avoid repeated API calls
        self.translation_cache = {}
    
    def detect_and_translate_to_english(self, text: str) -> Tuple[str, str, float]:
        """
        Detect language and translate to English if needed
        Returns: (english_text, detected_language, confidence)
        """
        try:
            # First use our language service for detection
            detected_lang, confidence = self.language_service.detect_language(text)
            
            # If already English, return as-is
            if detected_lang == 'en':
                return text, detected_lang, confidence
            
            # Check cache first
            cache_key = f"{detected_lang}:{text}"
            if cache_key in self.translation_cache:
                return self.translation_cache[cache_key], detected_lang, confidence
            
            # Translate to English
            translated = self.translator.translate(text, src=detected_lang, dest='en')
            english_text = translated.text
            
            # Cache the translation
            self.translation_cache[cache_key] = english_text
            
            print(f"Translated '{text}' ({detected_lang}) → '{english_text}' (en)")
            return english_text, detected_lang, confidence
            
        except Exception as e:
            print(f"Translation to English failed: {e}")
            # Fallback: return original text and assume English
            return text, 'en', 0.3
    
    def translate_response_to_user_language(self, english_response: str, target_language: str) -> str:
        """
        Translate English response back to user's language
        """
        try:
            # If target is English, return as-is
            if target_language == 'en':
                return english_response
            
            # Check cache first
            cache_key = f"en:{target_language}:{english_response}"
            if cache_key in self.translation_cache:
                return self.translation_cache[cache_key]
            
            # Translate from English to target language
            translated = self.translator.translate(english_response, src='en', dest=target_language)
            translated_text = translated.text
            
            # Cache the translation
            self.translation_cache[cache_key] = translated_text
            
            print(f"Translated response '{english_response[:50]}...' (en) → '{translated_text[:50]}...' ({target_language})")
            return translated_text
            
        except Exception as e:
            print(f"Translation to {target_language} failed: {e}")
            # Fallback: return English response with explanation
            fallback_msg = self.language_service.get_localized_response('error', target_language)
            if fallback_msg:
                return f"{fallback_msg}\n\n{english_response}"
            return english_response
    
    def is_translation_needed(self, language: str, confidence: float) -> bool:
        """
        Determine if translation is needed based on language and confidence
        """
        # Don't translate if English or very low confidence
        if language == 'en' or confidence < 0.4:
            return False
        
        # Don't translate if language not supported
        if language not in self.lang_mapping:
            return False
        
        return True
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get list of supported languages
        """
        return {
            'en': 'English',
            'fr': 'Français', 
            'rw': 'Kinyarwanda',
            'sw': 'Kiswahili',
            'es': 'Español',
            'de': 'Deutsch',
            'it': 'Italiano',
            'pt': 'Português'
        }
    
    def clear_cache(self):
        """Clear translation cache"""
        self.translation_cache.clear()
        print("Translation cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get translation cache statistics"""
        return {
            "cached_translations": len(self.translation_cache),
            "cache_size_mb": sum(len(k) + len(v) for k, v in self.translation_cache.items()) / 1024 / 1024
        }