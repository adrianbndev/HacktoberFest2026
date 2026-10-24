"""STUB de MOD-00: respuesta fija para probar el flujo de punta a punta. Track B (Adri) lo sustituye en MOD-03."""
from fastapi import APIRouter

from app.models.sdd import VisionAnalysisResult, VisionAnalyzeRequest, VisionFollowUpQuestion

router = APIRouter()

FOLLOW_UP_QUESTIONS = [
    VisionFollowUpQuestion(id="capacidad", question="¿Qué capacidad de almacenamiento tiene?",
                           reason="Entre 64 GB y otras versiones el precio cambia mucho.", affects="identification",
                           options=["64 GB", "32 GB", "No lo sé"]),
    VisionFollowUpQuestion(id="joycon", question="¿Los Joy-Con tienen drift o algún botón falla?",
                           reason="Es el defecto más habitual y no se ve en la foto.", affects="condition",
                           options=["Funcionan perfectos", "Drift leve", "Fallan"]),
    VisionFollowUpQuestion(id="accesorios", question="¿Qué incluye: caja, dock y cargador?",
                           reason="Venderla completa sube el precio medio.", affects="condition",
                           options=["Todo con caja", "Sin caja", "Solo la consola"]),
]


@router.post("/vision/analyze", response_model=VisionAnalysisResult, response_model_exclude_none=True)
def analyze(body: VisionAnalyzeRequest) -> VisionAnalysisResult:
    answered = bool(body.answers)
    return VisionAnalysisResult(
        name="Nintendo Switch OLED 64GB Blanca", category="Consolas y Videojuegos", brand="Nintendo",
        model="Switch OLED HEG-001", condition_score=88 if answered else 80, condition_label="Como nuevo",
        condition_reasoning="Pantalla sin arañazos visibles y carcasa limpia; leve desgaste en el dock.",
        seo_title="Nintendo Switch OLED Blanca 64GB como nueva + dock",
        seo_description="✅ Nintendo Switch OLED blanca en muy buen estado.\n📦 Envío por Wallapop o entrega en mano.",
        confidence=0.92 if answered else 0.64, follow_up_questions=[] if answered else FOLLOW_UP_QUESTIONS,
        source="deterministic_fallback",
    )
