import { getApp, getApps, initializeApp } from "firebase/app";
import { GoogleAuthProvider, getAuth } from "firebase/auth";

// Config pública de la app web (no es secreta: la seguridad está en Firebase Auth y en las reglas de Firestore).
// Proyecto en el plan gratuito Spark, sin facturación.
const firebaseConfig = {
  apiKey: "AIzaSyA2gahYlyseZKNT-T3o8LYiwh2nb1q9WMs",
  authDomain: "lifeos-recommerce-hf26.firebaseapp.com",
  projectId: "lifeos-recommerce-hf26",
  appId: "1:1084576324914:web:e1d9d4b791a403d823cb2b",
};

export const auth = getAuth(getApps().length ? getApp() : initializeApp(firebaseConfig));
export const googleProvider = new GoogleAuthProvider();
