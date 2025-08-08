import logging
import re
from typing import Dict, List
import httpx
from fastapi import HTTPException
from estnltk import Text
import difflib

from app.config import api_settings
from app.utils.sentence_aligner import vii_kokku_kirjandid
from app.utils.position_finder import find_correction_spans
from app.utils.ged_prelim_diff import build_differences

LOGGER = logging.getLogger(__name__)

HTTP_TIMEOUT = httpx.Timeout(60.0)

class GrammarService:
    def __init__(self):
        self.gec_ollama_url = api_settings.gec_ollama_url
        self.gee_ollama_url = api_settings.gee_ollama_url
        self.ged_ollama_url = api_settings.ged_ollama_url
        self.gec_model = api_settings.gec_model
        self.gee_model = api_settings.gee_model
        self.ged_model = api_settings.ged_model

    async def _make_ollama_request(self, ollama_url: str, model: str, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Make a request to Ollama API"""
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                headers={"Content-Type": "application/json"}, 
                json=data, 
            )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
        else:
            LOGGER.error(f"Ollama API error at {ollama_url}: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Error in Ollama API at {ollama_url}: {response.text}")

    async def correct_text(self, input_text: str, preceding_text: str | None = None) -> str:
        # Align prompt with raw EstGEC instruction format (context + explicit input sentence)
        # Preceding text is optional context from earlier sentences
        ctx = preceding_text or ""
        prompt = (
            "### Instruction:\n"
            "Reply with a corrected version of the input sentence in Estonian with all grammatical and spelling errors fixed. "
            "Refer to the preceding text (if any) for context. If there are no errors, reply with a copy of the original sentence.\n\n"
            "### Input:\n"
            f"Preceding text: {ctx}\n"
            f"Input sentence: {input_text}\n\n"
            "### Response:\n"
        )
        return await self._make_ollama_request(self.gec_ollama_url, self.gec_model, prompt, max_tokens=300, temperature=0.7)

    def _get_sentences(self, text: str):
        t = Text(text)
        try:
            return t.sentences
        except Exception:
            # Ensure the 'sentences' layer exists in case auto-tagging is disabled
            try:
                t.tag_layer('sentences')
                return t.sentences
            except Exception:
                # As a last resort, treat the whole text as one sentence-like span
                class Span:
                    def __init__(self, start, end):
                        self.start = start
                        self.end = end
                return [Span(0, len(text))]

    def _first_sentence_only(self, text: str) -> str:
        """Return only the first sentence of the given text."""
        sents = self._get_sentences(text)
        if not sents:
            return text
        s0 = sents[0]
        return text[s0.start:s0.end]

    def truncate_hallucinated_text(self, original: str, corrected: str) -> str:
        """Truncate corrected text if it has more sentences than the original."""
        orig_sents = self._get_sentences(original)
        corr_sents = self._get_sentences(corrected)
        
        if len(orig_sents) != len(corr_sents):
            return " ".join([corrected[s.start:s.end] for s in corr_sents[:len(orig_sents)]])
        return corrected

    def _get_words(self, text: str) -> List[str]:
        t = Text(text)
        try:
            words = t.words
        except Exception:
            try:
                t.tag_layer('words')
                words = t.words
            except Exception:
                # Fallback: simple whitespace split
                return text.split()
        return [text[w.start:w.end] for w in words]

    def _build_preliminary_differences(self, original: str, corrected: str) -> str:
        # Delegate to raw-aligned implementation based on Levenshtein ops and veadloetavaks mapping
        try:
            return build_differences(original, corrected)
        except Exception:
            # Fallback to simple difflib-based coarse differences (kept for robustness)
            o = self._get_words(original)
            c = self._get_words(corrected)
            sm = difflib.SequenceMatcher(a=o, b=c)
            lines: List[str] = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    continue
                orig = " ".join(o[i1:i2]).strip()
                repl = " ".join(c[j1:j2]).strip()
                if tag == 'replace':
                    if not orig and repl:
                        lines.append(f"Lisa: #{i1} #{i1} '' -> {repl}")
                    elif orig and not repl:
                        lines.append(f"Kustutamine: #{i1} #{i2} {orig} -> ''")
                    else:
                        lines.append(f"Asendus: #{i1} #{i2} {orig} -> {repl}")
                elif tag == 'delete' and orig:
                    lines.append(f"Kustutamine: #{i1} #{i2} {orig} -> ''")
                elif tag == 'insert' and repl:
                    lines.append(f"Lisa: #{i1} #{i1} '' -> {repl}")
            return "Erinevused:\n" + "\n".join(lines)

    async def generate_correction_log(self, original: str, corrected: str) -> str:
        # Match raw GED prompt: English instruction + filled 'Erinevused:' + 'Parandused:' header
        diffs = self._build_preliminary_differences(original, corrected)
        prompt = (
            "### Instruction:\n"
            "You are comparing two sentences: the original written by a language learner and the correct version of that sentence. "
            "Given that sentence pair and a preliminary list of differences, generate a list of corrections with error type, indices denoting which part of the original sentence was changed, original words and their correct counterpart.\n\n"
            "### Input:\n"
            f"Algne lause: {original}\n\n"
            f"Parandatud lause: {corrected}\n"
            f"{diffs}\n\n"
            "Parandused:"
        )
        return await self._make_ollama_request(self.ged_ollama_url, self.ged_model, prompt, max_tokens=400, temperature=0.7)

    def prepare_correction_log(self, correction_log: str) -> List[str]:
        """Preserve GED entries in raw format.
        - Keep lines like 'käändevorm: #3 #4 mulle -> mind'.
        - Drop the 'Parandused:' header and empty lines.
        - Strip any accidental leading numbering like '1. ' if present.
        - De-duplicate identical entries and normalize empty sides to '' while preserving order.
        """
        lines = [l.rstrip() for l in correction_log.splitlines()]
        items: List[str] = []
        for line in lines:
            if not line.strip():
                continue
            low = line.strip().lower()
            if low.startswith("parandused") or "parandused puuduvad" in low:
                continue
            cleaned = re.sub(r"^\s*\d+\.\s*", "", line).strip()
            if cleaned:
                items.append(cleaned)
        # Normalize and de-duplicate while preserving order
        return self._normalize_and_deduplicate_ged_entries(items)

    def _normalize_and_deduplicate_ged_entries(self, entries: List[str]) -> List[str]:
        """Normalize GED entries and remove duplicates while preserving order.
        - Condense spaces around '->'.
        - Ensure empty sides are represented as '' (two single quotes).
        - Keep the original label and indices intact.
        """
        seen = set()
        normalized: List[str] = []

        for raw in entries:
            line = (raw or "").strip()
            if not line:
                continue
            # Remove any leading numbering again just in case
            line = re.sub(r"^\s*\d+\.\s*", "", line).strip()
            # Normalize spaces around the arrow
            line = re.sub(r"\s*->\s*", " -> ", line)

            m = re.match(r'^\s*([^:]+):\s*#(\d+)\s+#(\d+)\s+(.*?)\s*->\s*(.*?)\s*$', line)
            if m:
                label, i1, i2, left, right = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)

                def norm_side(s: str) -> str:
                    s0 = (s or "").strip()
                    # If after removing quotes the side is empty, treat as ''
                    if re.sub(r"['\"“”„‟‹›‘’«»]", "", s0).strip() == "":
                        return "''"
                    return s0

                left_n = norm_side(left)
                right_n = norm_side(right)
                norm = f"{label.strip()}: #{int(i1)} #{int(i2)} {left_n} -> {right_n}"
            else:
                # Fallback normalization: collapse multiple spaces
                norm = re.sub(r"\s+", " ", line)

            if norm not in seen:
                seen.add(norm)
                normalized.append(norm)

        return normalized

    async def explain_correction(self, original: str, corrected: str, correction_details: str, specific_correction: str) -> str:
        prompt = (
            "### Instruction:\n"
            "Sa võrdled kahte eestikeelset lauset: keeleõppija kirjutatud algne lause ja parandatud lause. "
            "Sulle antakse paranduste loend, kus on vealiik, algne tekst ja parandatud tekst. Su ülesanne on selgitada ühte parandust. "
            "Selgita seda parandust, mis jägneb sõnale 'Selgitus'. Esiteks too välja põhjalikum selgitus, miks parandust vaja on. "
            "Teiseks anna lühike selgitus lihtsamas keeles. Pärast selgitust nimeta vealiik. Mitu vealiiki võivad kokku langeda. "
            "Omavahel seotud parandusi (näiteks sõnaühend, kus muutub mõlema sõna vorm) selgita koos. "
            "Sõnajärje parandusega kattuvaid muid parandusi selgita eraldi.\n\n"
            "### Input:\n"
            f"Algne lause: {original}\n"
            f"Parandatud lause: {corrected}\n\n"
            "Parandused:\n"
            f"{correction_details}\n"
            f"{specific_correction}\n\n"
            "### Response:\n"
        )
        return await self._make_ollama_request(self.gee_ollama_url, self.gee_model, prompt, max_tokens=220, temperature=0.5)

    async def process_request(self, text: str, language: str) -> Dict:
        corrected_text = await self.correct_text(text)
        # corrected_text = self.truncate_hallucinated_text(text, corrected_text)

        if text == corrected_text:
            return {
                "corrections": [],
                "corrected_text": text
            }

        corrections = []
        pos = 0 
        aligned_text = vii_kokku_kirjandid(text, corrected_text) or [(text, corrected_text)]

        for orig_sent, corr_sent in aligned_text:
            sent_start = text.find(orig_sent, pos)
            if sent_start == -1:
                continue

            pos = sent_start
            spans, pos = find_correction_spans(orig_sent, corr_sent, pos)
            corrections.extend(spans)
            pos = sent_start + len(orig_sent)

        return {
            "corrections": corrections,
            "corrected_text": corrected_text
        }

    async def process_request_v2(self, text: str, language: str) -> Dict:
        try:
            # Sentence-based processing: split original input and run GEC→GED→GEE per sentence
            sents = self._get_sentences(text)
            if not sents:
                return self._no_corrections_response(text)

            results: List[Dict] = []
            for i, s in enumerate(sents):
                orig_sent = text[s.start:s.end]
                preceding = text[:s.start].strip()
                corr_sent = await self.correct_text(orig_sent, preceding_text=preceding)
                # Clip to first sentence in case model returns more than one
                corr_sent = self._first_sentence_only(corr_sent)
                results.append(await self._process_sentence(orig_sent, corr_sent))

            return {"corrections": results}

        except Exception as e:
            LOGGER.error(f"Error processing request: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing grammar correction request")

    # Helper functions
    def _no_corrections_response(self, text: str) -> Dict:
        """Returns a response indicating no corrections were needed."""
        return {
            "corrections": [
                {
                    "original": text,
                    "corrected": text,
                    "correction_log": "Parandused puuduvad",
                    "explanations": "Parandused puuduvad",
                }
            ]
        }

    async def _process_sentence(self, input_sentence: str, corrected_sentence: str) -> Dict:
        """Processes a single sentence and generates correction logs and explanations."""
        if input_sentence == corrected_sentence:
            return {
                "original": input_sentence,
                "corrected": corrected_sentence,
                "correction_log": "Parandused puuduvad",
                "explanations": "Parandused puuduvad",
            }

        correction_log = await self.generate_correction_log(input_sentence, corrected_sentence)
        correction_entries = self.prepare_correction_log(correction_log)

        # Fallback: if GED returned nothing, synthesize entries using raw-style differences
        if not correction_entries:
            try:
                diffs_block = build_differences(input_sentence, corrected_sentence)
                # Drop header 'Erinevused:' and keep the lines
                correction_entries = [l for l in diffs_block.splitlines()[1:] if l.strip()]
            except Exception:
                correction_entries = []

        # Normalize and de-duplicate once more (covers both GED and fallback cases)
        correction_entries = self._normalize_and_deduplicate_ged_entries(correction_entries)

        if not correction_entries:
            return {
                "original": input_sentence,
                "corrected": corrected_sentence,
                "correction_log": "Parandused puuduvad",
                "explanations": "Parandused puuduvad",
            }
        
        log_string = "Parandused:\n" + "\n".join(correction_entries)
        explanations_list = []
        for i, entry in enumerate(correction_entries):
            explanation = await self._generate_explanation(input_sentence, corrected_sentence, log_string, entry, i)
            explanations_list.append(explanation)

        explanations = "\n\n".join(explanations_list)

        return {
            "original": input_sentence,
            "corrected": corrected_sentence,
            "correction_log": log_string,
            "explanations": explanations if explanations else "Parandused puuduvad",
        }

    async def _generate_explanation(self, input_sentence: str, corrected_sentence: str, log_string: str, correction_entry: str, index: int) -> str:
        """Generates an explanation for one correction without enforcing a fixed number of lines."""
        match = re.search(r'^[^:]*:\s*(.*)$', correction_entry)
        conversion = match.group(1) if match else correction_entry

        # Ask model (use 'Selgitus {n}. ...' to match prompt)
        explanation_raw = await self.explain_correction(
            input_sentence, corrected_sentence, log_string, f"Selgitus {index + 1}. {conversion}"
        )

        explanation = (explanation_raw or "").strip()
        if not explanation:
            explanation = f"Selgitus puudub. ({conversion})"

        header = f"Selgitus {index + 1}. {conversion}"
        return "\n".join([header, explanation])


grammar_service = GrammarService()
