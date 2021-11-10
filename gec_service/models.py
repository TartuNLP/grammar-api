from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class Language(str, Enum):
    estonian = "et"


class Span(BaseModel):
    start: int = Field(...,
                       description="Span start character index.",
                       example=0)
    end: int = Field(...,
                     description="Span end character index.",
                     example=6)


class Replacement(BaseModel):
    value: Optional[str] = Field(None,
                                 description="Suggested replacement text, null in case the span should be deleted.",
                                 example="Aitäh")


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
                      example="Aitähh!")


class GECResult(BaseModel):
    corrections: List[Correction] = Field(...,
                                          description="List of suggested corrections.")