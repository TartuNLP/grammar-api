import logging
import re
from typing import Dict, List
import httpx
from fastapi import HTTPException
from estnltk import Text

from app.config import api_settings
from app.utils.sentence_aligner import vii_kokku_kirjandid
from app.utils.position_finder import find_correction_spans

LOGGER = logging.getLogger(__name__)

class GrammarService:
    def __init__(self):
        self.auth = (api_settings.auth_username, api_settings.auth_password)

    async def correct_text(self, input_text: str) -> str:
        data = {
            "model": "tartuNLP/Llammas-base-p1-GPT-4o-human-error-mix-paragraph-GEC",
            "prompt": f"### Instruction:\nReply with a corrected version of the input essay in Estonian with all grammatical and spelling errors fixed. If there are no errors, reply with a copy of the original essay.\n\n### Input:\n{input_text}\n\n### Response:\n",
            "max_tokens": 1000,
            "temperature": 1
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_settings.gec_url,
                auth=self.auth, 
                headers={"Content-Type": "application/json"}, 
                json=data, 
            )
        if response.status_code == 200:
            return response.json()["choices"][0]["text"].strip()
        raise HTTPException(status_code=response.status_code, detail="Error in GEC API")

    def truncate_hallucinated_text(self, original: str, corrected: str) -> str:
        """Truncate corrected text if it has more sentences than the original."""
        input_text_obj = Text(original).tag_layer()
        corrected_text_obj = Text(corrected).tag_layer()
        
        if len(input_text_obj.sentences) != len(corrected_text_obj.sentences):
            return " ".join([s.enclosing_text for s in corrected_text_obj.sentences[:len(input_text_obj.sentences)]])
        return corrected

    async def generate_correction_log(self, original: str, corrected: str) -> str:
        data = {
            "model": "tartuNLP/Llammas-base-p1-GPT-4o-human-error-pseudo-m2",
            "prompt": f"### Instruction:\nSa võrdled kahte eestikeelset lauset: keeleõppija kirjutatud algne lause ja parandatud lause. Genereeri vea kaupa paranduste loend.\n\n### Input:\nAlgne tekst: {original}\n\nParandatud tekst: {corrected}\n\n### Response:\n",
            "max_tokens": 200,
            "temperature": 0.8
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_settings.m2_url,
                headers={"Content-Type": "application/json"},
                json=data,
            )
        if response.status_code == 200:
            return response.json()["choices"][0]["text"].strip()
        raise HTTPException(status_code=response.status_code, detail="Error in M2 API")

    def prepare_correction_log(self, correction_log: str) -> List[str]:
        """Prepare and number the correction log entries."""
        lines = correction_log.split('\n')
        numbered_lines = []
        offset = False
        
        for i, line in enumerate(lines):
            if i == 0 and "Parandused:" in line:
                continue
            elif i == 0 and "Parandused:" not in line:
                if "->" in line:
                    offset = True
            if offset:
                numbered_lines.append(f"{i+1}. {line}")
            else:
                numbered_lines.append(f"{i}. {line}")
        
        return numbered_lines

    async def explain_correction(self, original: str, corrected: str, correction_details: str, specific_correction: str) -> str:
        data = {
            "model": "tartuNLP/Llammas-base-p1-GPT-4o-human-error-explain-from-pseudo-m2",
            "prompt": f"### Instruction:\nSa võrdled kahte eestikeelset lauset: keeleõppija kirjutatud algne lause ja parandatud lause. Selgita ühte parandust.\n\n### Input:\nAlgne lause: {original}\n\nParandatud lause: {corrected}\n\nParandused:\n{correction_details}\n\n{specific_correction}\n\n### Response:\n1. Pikem selgitus (keeleline põhjendus, miks parandust vaja on).\n2. Lühike selgitus (lihtsustatud, et keeleõppija saaks paremini aru).\n3. Vealiik (nt. käändevorm, tegusõna vorm, õigekiri).",
            "max_tokens": 400,
            "temperature": 0.9
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_settings.explanation_url,
                headers={"Content-Type": "application/json"},
                json=data,
            )
        if response.status_code == 200:
            return response.json()["choices"][0]["text"].strip()
        raise HTTPException(status_code=response.status_code, detail="Error in Explanation API")


    async def process_request(self, text: str, language: str) -> Dict:
        corrected_text = await self.correct_text(text)
        corrected_text = self.truncate_hallucinated_text(text, corrected_text)

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
        # try:
            corrected_text = await self.correct_text(text)
            corrected_text = self.truncate_hallucinated_text(text, corrected_text)

            # If no corrections were made to the whole text, return early
            if text == corrected_text:
                return self._no_corrections_response(text)

            aligned_text = vii_kokku_kirjandid(text, corrected_text) or [(text, corrected_text)]
            results = []

            for input_sentence, corrected_sentence in aligned_text:
                results.append(await self._process_sentence(input_sentence, corrected_sentence))

            return {"corrections": results}

        # except Exception as e:
        #     LOGGER.error(f"Error processing request: {str(e)}")
        #     raise HTTPException(status_code=500, detail="Error processing grammar correction request")

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
            "explanations": explanations,
        }

    async def _generate_explanation(self, input_sentence: str, corrected_sentence: str, log_string: str, correction_entry: str, index: int) -> str:
        """Extracts the explanation for a correction entry."""
        match = re.search(r'^[^:]*:\s*(.*)$', correction_entry)
        conversion = match.group(1) if match else correction_entry[len(str(index + 1)) + 2:]

        explanation_input = f"Selgitus {index + 1}: {conversion}"
        explanation = await self.explain_correction(input_sentence, corrected_sentence, log_string, explanation_input)

        return f"{explanation_input}\n{explanation}"



grammar_service = GrammarService()
