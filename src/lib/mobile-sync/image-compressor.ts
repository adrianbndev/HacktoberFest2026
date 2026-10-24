// Las fotos del móvil pesan 5-15 MB: se reducen a JPEG <= 800 px (~150 KB) antes de subirlas
// (.agent/rules/hackathon-guardrails.md §1.3).
const MOBILE_IMAGE_MAX_DIMENSION_PX = 800;
const MOBILE_IMAGE_JPEG_QUALITY = 0.75;

export async function compressImageFileToDataUrl(file: File): Promise<string> {
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = objectUrl;
    await image.decode();
    const scale = Math.min(1, MOBILE_IMAGE_MAX_DIMENSION_PX / Math.max(image.naturalWidth, image.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Canvas 2D no disponible");
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", MOBILE_IMAGE_JPEG_QUALITY);
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
