from app.models.domain import VisionAnalysisWithFollowUp, VisionAnalyzeRequestWithAnswers

QUESTION = {"id": "capacidad", "question": "¿Qué capacidad tiene?", "reason": "Cambia el precio",
            "affects": "identification", "options": ["64 GB", "32 GB"]}


def test_preguntas_de_seguimiento_amplian_el_contrato_de_vision() -> None:
    analysis = VisionAnalysisWithFollowUp.model_validate({
        "name": "Nintendo Switch OLED", "category": "Consolas", "brand": "Nintendo", "model": "HEG-001",
        "conditionScore": 95, "conditionLabel": "Buen estado", "conditionReasoning": "Pantalla impecable",
        "seoTitle": "Nintendo Switch OLED como nueva", "seoDescription": "Consola en perfecto estado, con caja.",
        "confidence": 0.6, "followUpQuestions": [QUESTION],
    })
    assert analysis.condition_label == "Nuevo"  # la rúbrica de Track B se sigue aplicando
    assert analysis.model_dump(by_alias=True)["followUpQuestions"][0]["affects"] == "identification"

    without_questions = analysis.model_dump(exclude={"confidence", "follow_up_questions"})
    assert VisionAnalysisWithFollowUp.model_validate(without_questions).follow_up_questions == []

    request = VisionAnalyzeRequestWithAnswers.model_validate({
        "photoDataUrl": "data:image/jpeg;base64,AAAA",
        "answers": [{"questionId": "capacidad", "question": QUESTION["question"], "answer": "64 GB"}],
    })
    assert request.answers[0].answer == "64 GB"
