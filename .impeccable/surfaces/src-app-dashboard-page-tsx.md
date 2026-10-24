---
version: 1
slug: "src-app-dashboard-page-tsx"
primary_target: "src/app/(dashboard)/page.tsx"
related_targets: ["src/components/dashboard","src/components/inventory"]
---

# Surface brief: dashboard (Inicio + Mi inventario)

Mode: Operate. Público: jurado y participantes de la hackathon viendo la demo en proyector (sala iluminada); el presentador tasa con su móvil.

Indicación del usuario: la Home no lleva imágenes; muestra los datos clave y las últimas tasaciones. Las fotos viven en «Mi inventario» (/inventario).

Fuera de alcance por ahora: archivos de `src/components/mobile-sync/` con trabajo de Ales (DynamicProductForm y partes del modal, el hook y la pantalla móvil), salvo que Matías lo confirme. Nada de niveles 2-4 (tendencias, alertas, LifeOS).

## Direction contract

THESIS: Tus objetos como una cuenta bancaria: el patrimonio es el saldo y cada tasación es un movimiento que entra. Rechaza el bento de tarjetas de cifras iguales y el muro de fichas con foto en la Home.

OWN-WORLD: Banca móvil. Fondo blanco con superficies gris niebla (#EEF0F3), tinta #101114 y un solo acento índigo eléctrico (#4B3BFF): el bloque del saldo es un campo de acento con texto blanco (la «tarjeta» de la cuenta), y fuera de él el acento solo marca la acción principal, la pestaña activa y el dinero que entra. Saldo gigante en Funnel Display con cifras tabulares; interfaz en Funnel Sans. Filas de movimientos con icono de categoría en círculo tintado e importes alineados a la derecha; píldoras, tarjetas de radio amplio (20 px fuera, 12 px dentro), sin bordes de sobra.

STORY: En 5 s el jurado ve cuánto vale todo, entiende que cada objeto es dinero con horquilla y origen, y ve entrar una tasación nueva como una transferencia. El presentador pulsa «Tasar un objeto», hace la foto y el saldo sube.

FIRST VIEWPORT: Barra con el logotipo SmartLoot, pestañas Inicio / Mi inventario y la cuenta. Bloque de saldo: «Tu patrimonio», el total (precio justo) a ~96 px en escritorio, debajo la horquilla venta rápida–máximo como regla con marcador y la línea de origen; dos acciones en píldora: «Tasar un objeto» (blanca) y «Mi inventario»; en escritorio el saldo va a la izquierda y las tasaciones recientes a la derecha, todo en la primera pantalla. «Tasaciones recientes», hasta 5 filas sin fotos agrupadas por día, con «Ver todo».

SIGNATURE: El saldo cuenta. Al llegar una tasación, el patrimonio rueda de la cifra vieja a la nueva y la fila entra arriba con «+159 €»; con reduced-motion el cambio es instantáneo.

FORM: Banca móvil, candidato 1 de mi lista ordenada (elegido como IMPECCABLE’S PICK tras un re-roll con indicación del usuario). Seed key b729419b.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
