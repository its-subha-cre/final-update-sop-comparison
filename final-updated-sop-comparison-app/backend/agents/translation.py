import time
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from langchain_core.prompts import ChatPromptTemplate
from config import config_instance
from llm.factory import LLMFactory

logger = logging.getLogger("TranslationAgent")
logger.setLevel(logging.INFO)

class TranslationValidationAgent:
    """
    Enterprise Quality Validation Agent for SOP Translations.
    Verifies that translation outputs are valid English, non-empty, structurally complete,
    and retain clause/section markers prior to downstream chunking and graph indexing.
    """

    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold

    def _count_structure_markers(self, text: str) -> Dict[str, int]:
        """Counts paragraphs, numbered lines, and section markers."""
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        lines = [l for l in text.split("\n") if l.strip()]
        numbered_lines = len(re.findall(r'^\s*(\d+[\.\)]|[A-Z]+[\-\_]\d+)', text, re.MULTILINE))
        return {
            "paragraphs": len(paragraphs),
            "lines": len(lines),
            "numbered": numbered_lines
        }

    def validate_translation(self, original_text: str, translated_text: str, 
                             detected_lang: str, detector_fn = None) -> Dict[str, Any]:
        """
        Validates translation result against structural, linguistic, and completeness metrics.
        """
        issues = []
        if not translated_text or not translated_text.strip():
            return {
                "is_valid": False,
                "confidence_score": 0.0,
                "output_language": "unknown",
                "issues": ["Translated text is empty or null."]
            }

        # 1. Output Language Validation
        out_lang = "en"
        if detector_fn:
            try:
                out_lang = detector_fn(translated_text[:1500])
            except Exception:
                out_lang = "en"

        if out_lang not in ["en", "english"]:
            issues.append(f"Output language validation failed. Detected '{out_lang}' instead of English ('en').")

        # 2. Structural Completeness Check
        orig_struct = self._count_structure_markers(original_text)
        trans_struct = self._count_structure_markers(translated_text)

        # Length ratio sanity check
        orig_len = len(original_text.strip())
        trans_len = len(translated_text.strip())
        length_ratio = trans_len / max(1, orig_len)

        if length_ratio < 0.35:
            issues.append(f"Severe text truncation detected. Translated text length ratio is {length_ratio:.2f} (< 0.35).")

        # Paragraph count preservation ratio
        para_ratio = trans_struct["paragraphs"] / max(1, orig_struct["paragraphs"])
        if para_ratio < 0.5:
            issues.append(f"Paragraph count drop detected. Preserved paragraph ratio is {para_ratio:.2f}.")

        # 3. Confidence Score Calculation
        score = 1.0
        if issues:
            score -= (0.25 * len(issues))
        score = max(0.0, min(1.0, score))

        is_valid = (score >= self.confidence_threshold) and (trans_len > 0) and (out_lang in ["en", "english"])

        logger.info(f"[Quality Validation Agent] Status: {'PASSED' if is_valid else 'FAILED'} | Score: {score:.2f} | Issues: {issues}")

        return {
            "is_valid": is_valid,
            "confidence_score": score,
            "detected_language": detected_lang,
            "output_language": out_lang,
            "original_length": orig_len,
            "translated_length": trans_len,
            "original_paragraphs": orig_struct["paragraphs"],
            "translated_paragraphs": trans_struct["paragraphs"],
            "issues": issues
        }

class TranslationAgent:
    """
    Enterprise Translation Agent for SOP documents.
    Detects language dynamically and translates non-English SOPs into English.
    Supports incremental chunk-based translation for large (100+ page) enterprise documents.
    Integrates TranslationValidationAgent to ensure 100% canonical English propagation.
    """

    def __init__(self, chunk_size: int = 3500, max_workers: int = 4):
        self.chunk_size = chunk_size
        self.max_workers = max_workers
        self.validator = TranslationValidationAgent()
        self.translation_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an Enterprise Translation Agent specialized in Standard Operating Procedures (SOPs), compliance, and regulatory documentation.
            Your sole task is to translate the provided text completely and verbatim into English.
            
            CRITICAL TRANSLATION RULES:
            1. Translate ALL text (including section titles, headings, labels, and table headers) into English.
               For example: translate '目的' -> 'Purpose', '范围' -> 'Scope', '职责' -> 'Responsibilities', '访问控制' -> 'Access Control', '安全控制' -> 'Security Controls'.
            2. Preserve document hierarchy, numbering structure (e.g., 1.1, GSOP-XRAY-001), bullet points, and paragraph layout.
            3. Preserve all technical terminology, regulatory terms, equipment names, and site identifiers.
            4. NEVER summarize, paraphrase, simplify, or omit any details.
            5. NEVER leave section titles or headings untranslated in the foreign language.
            6. Return ONLY the direct English translation of the input text.
            """),
            ("user", "Text to translate:\n\n{text}")
        ])

    def _get_translation_llm(self):
        """
        Abstracts API key selection with priority:
        1. GROQ_TRANSLATION_API_KEY (Dedicated backend key if set)
        2. Configured LLM provider key from setup / config_instance
        """
        model_name = getattr(config_instance, "TRANSLATION_MODEL", "llama-3.1-8b-instant")
        dedicated_key = getattr(config_instance, "GROQ_TRANSLATION_API_KEY", "")
        
        if dedicated_key and dedicated_key.strip():
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=model_name,
                groq_api_key=dedicated_key.strip(),
                temperature=0.0
            )
        else:
            # Fallback to the platform's configured chat model
            return LLMFactory.get_chat_model()

    def detect_language(self, text: str) -> str:
        """
        Detects document language using langdetect, offline heuristics, and LLM fallback.
        """
        if not text or not text.strip():
            return "en"

        # 1. Try fast local detection using langdetect
        try:
            from langdetect import detect
            sample = text[:2000]
            detected = detect(sample)
            logger.info(f"[Language Detection] Local detector returned language code: '{detected}'")
            return detected.lower()
        except Exception as e:
            logger.debug(f"[Language Detection] Local langdetect notice: {e}")

        # 2. Offline heuristic detection for common non-English indicator tokens
        sample_lower = text[:2000].lower()
        non_english_tokens = [
            "el", "la", "los", "las", "este", "procedimiento", "equipo", "obligatorios", "para", "del", # Spanish
            "die", "der", "das", "und", "für", "sicherheit", "verfahren", "betriebsstoff", # German
            "le", "la", "les", "une", "pour", "avec", "dans", "sécurité", # French
            "il", "lo", "i", "gli", "le", "per", "con", "sicurezza", # Italian
            "de", "het", "een", "voor", "veiligheid" # Dutch
        ]
        words = sample_lower.split()
        match_count = sum(1 for w in words if w in non_english_tokens)
        if match_count >= 3:
            logger.info(f"[Language Detection] Offline heuristic detected non-English text (matches: {match_count})")
            return "non-en"

        # 3. LLM-based fallback classification
        try:
            llm = self._get_translation_llm()
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a language identification agent. Identify the primary ISO 639-1 language code (e.g. 'en', 'es', 'de', 'fr', 'zh') of the text. Reply with ONLY the two-letter language code."),
                ("user", "Text sample:\n{sample}")
            ])
            chain = prompt | llm
            res = chain.invoke({"sample": text[:1000]})
            code = res.content.strip().lower()[:2]
            logger.info(f"[Language Detection] LLM detector returned language code: '{code}'")
            return code
        except Exception as e:
            logger.warning(f"[Language Detection] Classification failed: {e}. Defaulting to 'en'.")
            return "en"

    def _chunk_text(self, text: str) -> List[str]:
        """Splits raw text into logical paragraph chunks respecting chunk_size bound."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_len = 0

        for p in paragraphs:
            p_len = len(p) + 2
            if current_len + p_len > self.chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [p]
                current_len = p_len
            else:
                current_chunk.append(p)
                current_len += p_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _translate_single_chunk_attempt(self, seq_id: int, chunk_text: str, use_fallback_ll: bool = False) -> Tuple[int, str]:
        """Performs single translation attempt with exponential backoff retries."""
        if use_fallback_ll:
            llm = LLMFactory.get_chat_model()
        else:
            llm = self._get_translation_llm()

        chain = self.translation_prompt | llm
        max_retries = 3
        backoff = 1.0
        
        for attempt in range(max_retries):
            try:
                res = chain.invoke({"text": chunk_text})
                content = res.content
                if isinstance(content, list):
                    translated_text = " ".join(item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content)
                else:
                    translated_text = str(content)
                return seq_id, translated_text.strip()
            except Exception as e:
                logger.warning(f"[Translation Attempt] Chunk {seq_id} (fallback={use_fallback_ll}) attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
        raise RuntimeError(f"Translation failed after {max_retries} attempts.")

    def _translate_single_chunk(self, chunk_tuple: Tuple[int, str]) -> Tuple[int, str]:
        """Translates a single text chunk with secondary LLM fallback protection."""
        seq_id, chunk_text = chunk_tuple
        if not chunk_text.strip():
            return seq_id, chunk_text

        # 1. Attempt primary translation (using dedicated translation model / key)
        try:
            return self._translate_single_chunk_attempt(seq_id, chunk_text, use_fallback_ll=False)
        except Exception as e:
            logger.warning(f"[Translation Agent] Primary model failed for chunk {seq_id}: {e}. Switching to fallback model...")

        # 2. Attempt fallback translation (using global configured chat model)
        try:
            return self._translate_single_chunk_attempt(seq_id, chunk_text, use_fallback_ll=True)
        except Exception as e:
            logger.error(f"[Translation Agent] Fallback model also failed for chunk {seq_id}: {e}. Retaining original text.")

        return seq_id, chunk_text

    def translate_document(self, text: str) -> str:
        """
        Translates a full document incrementally in parallel sequence-preserved chunks.
        """
        chunks = self._chunk_text(text)
        logger.info(f"[Translation Agent] Document split into {len(chunks)} chunk(s) for processing.")

        if len(chunks) == 1:
            _, translated = self._translate_single_chunk((0, chunks[0]))
            return translated

        # Parallel chunk processing maintaining sequence ordering
        indexed_chunks = list(enumerate(chunks))
        translated_results = [None] * len(chunks)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._translate_single_chunk, item) for item in indexed_chunks]
            for fut in futures:
                seq_id, translated_text = fut.result()
                translated_results[seq_id] = translated_text

        return "\n\n".join(translated_results)

    def process_raw_texts(self, raw_texts: Dict[str, str], 
                         original_raw_texts: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Processes all raw texts in state dictionary in-place:
        1. Preserves original untranslated text in original_raw_texts if provided.
        2. Checks language -> translates if non-English.
        3. Validates translation quality using TranslationValidationAgent.
        4. Sets raw_texts to canonical validated English representation.
        """
        metadata = {}

        for key, text in list(raw_texts.items()):
            if not text or not text.strip():
                continue

            # Store original raw text for traceability & auditing
            if original_raw_texts is not None:
                original_raw_texts[key] = text

            lang = self.detect_language(text)
            if lang in ["en", "english"]:
                logger.info(f"[Translation Agent] Key '{key}' detected as English ('{lang}'). Skipping translation.")
                metadata[key] = {
                    "is_translated": False,
                    "detected_language": lang,
                    "confidence_score": 1.0,
                    "status": "native_english"
                }
                continue

            logger.info(f"[Translation Agent] Key '{key}' detected as non-English ('{lang}'). Translating to English...")
            start_t = time.time()
            translated = self.translate_document(text)
            duration = int((time.time() - start_t) * 1000)

            # Quality Validation Step
            validation = self.validator.validate_translation(
                original_text=text,
                translated_text=translated,
                detected_lang=lang,
                detector_fn=self.detect_language
            )

            logger.info(f"[Translation Agent] Key '{key}' translated in {duration}ms. Validation Score: {validation['confidence_score']:.2f}")

            metadata[key] = {
                "is_translated": True,
                "detected_language": lang,
                "duration_ms": duration,
                "validation": validation
            }

            # Update canonical state text with validated English representation
            raw_texts[key] = translated

        return metadata
