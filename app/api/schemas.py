from typing import List, Optional

from pydantic import BaseModel, Field, validator

from app import api_settings


class Span(BaseModel):
    start: int = Field(...,
                       description="Span start character index.",
                       example=0)
    end: int = Field(...,
                     description="Span end character index.",
                     example=6)
    value: str = Field(...,
                       description="Span value in original text.",
                       example="Aitähh!")


class Replacement(BaseModel):
    value: Optional[str] = Field(None,
                                 description="Suggested replacement text, null in case the span should be deleted.",
                                 example="Aitäh!")


class Correction(BaseModel):
    span: Span = Field(...,
                       description="Span that the suggestion applies to. Each span must be longer than 0 characters, "
                                   "must contain non-whitespace characters, consist of full tokens "
                                   "(words or punctuation marks, multi-token spans are allowed). "
                                   "In case a new word should be added or a whitespace related error, "
                                   "the span will refer to the preceding or following token(s) (or both).")
    replacements: List[Replacement]


class GECRequest(BaseModel):
    language: str = Field(api_settings.languages[0],
                          description="Input language ISO 2-letter code.")
    text: str = Field(...,
                      description="Original text input. May contain multiple sentences.",
                      example="Aitähh!",
                      max_length=api_settings.max_input_length)

    @validator('language')
    def validate_language(cls, v):
        if v not in api_settings.languages:
            raise ValueError(f"Unsupported language '{v}'.")
        return v


class CorrectionEntry(BaseModel):
    original: str = Field(..., description="Original sentence")
    corrected: str = Field(..., description="Corrected sentence")
    correction_log: str = Field(..., description="Detailed correction log for the sentence")
    explanations: str = Field(..., description="Explanation for the corrections in the sentence")

class GECResult(BaseModel):
    corrections: List[CorrectionEntry] = Field(..., description="List of sentence corrections")

