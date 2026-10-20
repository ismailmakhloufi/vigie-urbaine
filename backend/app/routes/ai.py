"""
Urban Butterfly - AI Router (etape 11)

POST /ai/ask       : chat explicatif (question en français -> réponse liée aux faits)
POST /ai/briefing  : rapport de situation complet pour la cellule de crise
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai import answer_question, generate_briefing


router = APIRouter(prefix="/ai", tags=["AI"])


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@router.post("/ask")
def ask(request: AskRequest):
    try:
        return answer_question(request.question)
    except Exception as exc:
        raise HTTPException(500, f"AI error: {exc}")


@router.post("/briefing")
def briefing():
    try:
        return generate_briefing()
    except Exception as exc:
        raise HTTPException(500, f"AI error: {exc}")
