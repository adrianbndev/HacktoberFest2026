import { Suspense } from "react";
import { MobileCaptureScreen } from "@/components/mobile-sync/MobileCaptureScreen";

// El sessionId solo se conoce al abrir el QR: con cacheComponents, useParams necesita un Suspense.
export default function MobileCapturePage() {
  return (
    <Suspense fallback={<p className="p-6 text-center">Conectando con el PC…</p>}>
      <MobileCaptureScreen />
    </Suspense>
  );
}
