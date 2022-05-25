from typing import List, Optional

from pydantic import BaseModel, Field

from app import api_settings
from . import Language


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
    language: Language = Field(Language.estonian,
                               description="Input language ISO 2-letter code.")
    text: str = Field(...,
                      description="Original text input. May contain multiple sentences.",
                      example="Aitähh!",
                      max_length=api_settings.max_input_length)


class GECResult(BaseModel):
    corrections: List[Correction] = Field(...,
                                          description="List of suggested corrections.")
    corrected_text: str = Field(...,
                                description="[DEPRECATED] Suggested value for the correct output. "
                                            "This value will be deprecated in future releases.",
                                example="Aitäh!")
