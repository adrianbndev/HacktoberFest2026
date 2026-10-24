// Preguntas de seguimiento de la Visión IA: una sola foto no basta para identificar el producto ni su estado,
// así que la IA puede preguntar y el cliente reenvía la foto con las respuestas para afinar el análisis.
// Amplía las interfaces de Visión de sdd.ts (Track B) sin modificarlas (module augmentation); todos los campos
// son opcionales, así que los proveedores actuales siguen siendo válidos. Espejo de backend/app/models/domain.py.
import "@/types/sdd";

export interface VisionFollowUpQuestion {
  id: string;
  question: string;               // Ej. "¿Qué capacidad de almacenamiento tiene?"
  reason: string;                 // Por qué importa para identificar o tasar
  affects: 'identification' | 'condition';
  options: string[];              // Respuestas rápidas (vacío = respuesta libre)
}

export interface VisionAnswer {
  questionId: string;
  question: string;
  answer: string;
}

declare module "@/types/sdd" {
  interface VisionAnalyzeRequest {
    answers?: VisionAnswer[];     // Respuestas a followUpQuestions anteriores
  }

  interface VisionAnalysisResult {
    confidence?: number;          // 0 a 1
    followUpQuestions?: VisionFollowUpQuestion[];  // Vacío o ausente = la IA no necesita más datos
  }
}
