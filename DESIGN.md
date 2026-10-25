---
name: SmartLoot
description: Tus objetos como una cuenta bancaria; el patrimonio es el saldo y cada tasación es un movimiento que entra.
colors:
  paper: "#ffffff"
  fog: "#eef0f3"
  fog-2: "#e2e5ea"
  line: "#d7dbe1"
  ink: "#101114"
  ink-2: "#5b606b"
  accent: "#0b6b3a"
  accent-hover: "#095530"
  accent-soft: "#e6f9ef"
  on-accent-2: "#d7f5e6"
  wear-tint: "oklch(98.7% 0.022 95.277)"
  wear-ink: "oklch(47.3% 0.137 46.201)"
  wear-fill: "oklch(66.6% 0.179 58.318)"
  parts-tint: "oklch(96.9% 0.015 12.422)"
  parts-ink: "oklch(45.5% 0.188 13.697)"
  parts-fill: "oklch(58.6% 0.253 17.585)"
  danger: "oklch(51.4% 0.222 16.935)"
  danger-hover: "oklch(45.5% 0.188 13.697)"
typography:
  display:
    fontFamily: "Funnel Display, system-ui, sans-serif"
    fontSize: "clamp(3.5rem, 8vw, 6rem)"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.04em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Funnel Display, system-ui, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  figure:
    fontFamily: "Funnel Display, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.03em"
    fontFeature: "tnum"
  title:
    fontFamily: "Funnel Sans, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Funnel Sans, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  control:
    fontFamily: "Funnel Sans, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.4
  label:
    fontFamily: "Funnel Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  inner: "12px"
  panel: "20px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  2xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.paper}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "0 24px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-on-accent:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.accent}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "0 24px"
    height: "48px"
  button-secondary:
    backgroundColor: "{colors.fog}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "0 20px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.fog-2}"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.paper}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "0 20px"
    height: "44px"
  button-danger-hover:
    backgroundColor: "{colors.danger-hover}"
  nav-tabs:
    backgroundColor: "{colors.fog}"
    rounded: "{rounded.pill}"
    padding: "4px"
  nav-tab:
    textColor: "{colors.ink-2}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "0 20px"
    height: "40px"
  nav-tab-active:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.accent}"
  balance-panel:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.paper}"
    rounded: "{rounded.panel}"
    padding: "32px"
  panel:
    backgroundColor: "{colors.fog}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "16px"
  movement-row:
    textColor: "{colors.ink}"
    rounded: "{rounded.inner}"
    padding: "12px"
  movement-row-hover:
    backgroundColor: "{colors.paper}"
  chip-condition:
    backgroundColor: "{colors.fog-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "4px 12px 4px 10px"
  chip-condition-wear:
    backgroundColor: "{colors.wear-tint}"
    textColor: "{colors.wear-ink}"
  chip-condition-parts:
    backgroundColor: "{colors.parts-tint}"
    textColor: "{colors.parts-ink}"
  input-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.inner}"
    padding: "0 14px"
    height: "44px"
  dialog:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "28px"
---

# Design System: SmartLoot

## Overview

**Creative North Star: "The Object Account"**

SmartLoot reads like a mobile banking app whose currency is the stuff in your house. Total patrimony is the balance; every valuation is a movement that comes in. The world is white paper with fog-grey surfaces, near-black ink and one deep emerald. The balance block is the "card" of the account: a solid accent field with white type. Outside it, the accent only marks the primary action, the active tab and money arriving.

Density is calm and legible from the back of a lit projection room: big tabular figures, 15px semibold controls, generous 20px panel corners, no borders where a tonal step will do. Euro amounts are always tabular and right-aligned in lists. Every price is shown as a range (venta rápida to máximo) with the fair price marked where it really falls, never as a lone number.

The system is light mode only, on purpose: the demo is projected in a lit room. Do not add a dark variant without a deliberate decision.

**Key Characteristics:**
- One accent (deep emerald) used as a field once per screen and as a signal elsewhere.
- Tonal layering (paper / fog / fog-2) instead of borders and shadows.
- Funnel Display for money and page titles, Funnel Sans for everything else.
- Pills for every control and status; 20px outer, 12px inner radii.
- Prices as rulers: a horquilla with a marker, not three equal cards.

## Colors

A cool neutral bank-app ground with a single deep emerald; warm colors appear only to warn.

### Primary
- **Deep Emerald** (accent): the balance field, primary buttons, the active nav tab, link-like actions ("Ver todo", "Buscar"), the range ruler marker, focus outlines, caret and text selection, and the "+amount" of a newly arrived valuation. 6.6:1 against white and 5.8:1 on fog.
- **Pressed Emerald** (accent-hover): hover state of accent-filled buttons only.
- **Emerald Wash** (accent-soft): the transient tint a new movement row arrives with, fading to nothing.
- **Emerald Mist** (on-accent-2): secondary text on the accent field (labels, explanations). 5.7:1 on accent.

### Neutral
- **Paper** (paper): page background, dialogs, menus, icon discs and secondary buttons that sit on fog.
- **Fog** (fog): every panel and card surface; the nav-tab track; secondary buttons on paper.
- **Deep Fog** (fog-2): one step deeper: condition chips, photo wells, ruler tracks, skeletons, hover of fog buttons.
- **Hairline** (line): the only stroke color: input borders, `details` dividers inside cards, menu ring.
- **Ink** (ink): primary text and the sold-status pill; the login CTA background.
- **Slate** (ink-2): secondary text, metadata, labels. 6.3:1 on paper, 5.4:1 on fog.

### Semantic (status only)
- **Wear Amber** (wear-tint / wear-ink / wear-fill): the "Desgaste visible" condition chip and meter.
- **Parts Rose** (parts-tint / parts-ink / parts-fill): the "Para piezas" condition chip and meter.
- **Danger Rose** (danger / danger-hover): destructive confirmations, destructive menu items and inline error text.

### Named Rules
**The One Field Rule.** The accent appears as a filled field once per screen (the balance block on Inicio, the example aside on login). Everywhere else it is a signal: one primary button, the active tab, an arriving amount.

**The Warm Means Value Lost Rule.** Amber and rose are reserved for condition states that subtract value and for destructive actions. Positive and neutral conditions stay ink on fog; the grade bars carry the level, not the color.

## Typography

**Display Font:** Funnel Display (with system-ui, sans-serif)
**Body Font:** Funnel Sans (with system-ui, sans-serif)

**Character:** A matched superfamily: the display cut is tight and confident for money, the sans is plain and friendly for interface. Both loaded via next/font as `--font-funnel-display` / `--font-funnel-sans`.

### Hierarchy
- **Display** (600, clamp(3.5rem, 8vw, 6rem), 1, -0.04em, tabular): the patrimony balance only. The login hero uses the same face at clamp(2.5rem, 5.2vw, 4rem), 1.02, -0.035em, balanced.
- **Headline** (600, 2.25rem, -0.03em): page titles ("Mi inventario").
- **Figure** (600, 2rem, -0.03em, tabular): the fair price on an item card; 3rem on the login example card.
- **Title** (Funnel Sans 600, 1.25rem): panel headings ("Tasaciones recientes"); dialog titles at 1.125rem; item names at 17px.
- **Body** (400, 1rem, 1.5): explanations, empty states; secondary lines at 0.875rem in slate.
- **Control** (600, 15px): buttons, tabs, summaries, links, amounts in lists.
- **Label** (400, 13px): ruler labels ("Venta rápida", "Máximo", "Precio justo"), field captions, chips (600).

### Named Rules
**The Tabular Money Rule.** Every euro amount uses tabular numerals; in lists it is right-aligned with its range underneath in slate.

**The Display Is For Money Rule.** Funnel Display is used for amounts, page titles, the login hero and the wordmark; never for body copy, buttons or labels.

## Layout

A centred column (max 72rem / 1152px) with 16px side padding (24px from 640px), 16px top (24px from 1024px), and 32px between the top bar and content. Home is a two-column grid from 1024px (balance at ~1.12fr left, panels at 1fr right, 20px gap; 16px gap stacked); the balance block stretches to the right column's height and pushes its actions to the bottom. Inventory is a 1 / 2 / 3 column card grid (640px / 1024px) with 16px gaps. Panels pad 12px (16px from 640px) and their rows pad 12px, so content aligns to a 24-28px inset; the balance and empty/error panels pad 24-32px. On narrow screens the nav tabs drop to a full-width row under logo and account.

## Elevation & Depth

Flat by default. Depth comes from tonal steps (paper, fog, fog-2) and from the accent field. Shadows exist only on things that float above the page or sit on a photo, always ink-tinted and soft.

### Shadow Vocabulary
- **Tab lift** (`box-shadow: 0 1px 3px rgb(16 17 20 / 0.1)`): the active tab inside the fog track.
- **Pill on photo** (`box-shadow: 0 2px 8px rgb(16 17 20 / 0.15)`): status pill over an item image.
- **Popover** (`box-shadow: 0 12px 32px -8px rgb(16 17 20 / 0.22), 0 2px 6px rgb(16 17 20 / 0.06)`): menus, with a hairline ring.
- **Toast** (`box-shadow: 0 12px 32px -8px rgb(16 17 20 / 0.4)`): the ink status toast at the bottom.
- **Showcase** (`box-shadow: 0 32px 64px -24px rgb(16 17 20 / 0.45)`): the paper example card on the login accent aside.

Dialogs use a native backdrop of ink at 50%, no shadow.

### Named Rules
**The Tone Before Shadow Rule.** A panel is separated by fog on paper (or paper on fog), never by a shadow or a border. Shadows are only for floating layers.

## Shapes

Soft and rounded throughout. Outer containers (panels, cards, dialogs, the balance block) use the panel radius; inner surfaces (rows, inputs, menu panels, info boxes, skeleton blocks) use the inner radius. Every control, chip, tab and status tag is a full pill; icon buttons and icon discs are circles. Strokes are rare: a hairline divider above a card's `details`, a white/20 divider inside the balance block, input borders. Ruler tracks and meters are 6px pill bars; the ruler marker is a 3px x 14px pill.

## Components

### Buttons
Tactile pills with a single filled voice per screen.
- **Shape:** full pill, 48px tall for primary actions, 44px for dialog and secondary actions.
- **Primary:** accent fill, white control text, 24px side padding, optional 20px leading icon; hover to pressed emerald.
- **On accent:** inside the balance field the primary becomes a white pill with accent text (hover scales to 1.02, active 0.98); its companion is a translucent white/12 pill with a white/35 inset ring.
- **Secondary:** fog pill on paper (hover fog-2), or paper pill on fog inside cards ("Copiar anuncio", hover fog-2). Icon-only buttons are 36-44px circles.
- **Danger:** danger rose fill, white text, only in confirmation dialogs.
- **Focus:** 2px accent outline at 2px offset globally; white outline on the accent field.

### Chips
- **Condition chip:** pill, 13px semibold, with five 4px x 10px grade bars before the label (filled to the grade, the rest at 20% of current color). Ink on fog-2 for Nuevo, Como nuevo, Buen estado; amber for Desgaste visible; rose for Para piezas.
- **Status tag:** paper pill (ink pill when sold) over the photo, top-left, with the pill-on-photo shadow. "Foto de ejemplo" and "Ejemplo" are paper/fog pills that honestly label placeholder content.

### Cards / Containers
- **Corner Style:** panel radius outside, inner radius inside.
- **Background:** fog on paper; inner info boxes are fog on paper dialogs.
- **Shadow Strategy:** none (see Elevation).
- **Border:** none; a hairline divider only above collapsible details.
- **Internal Padding:** 20px in item cards, 12-16px in list panels, 24-32px in the balance and empty states.
- **Item card:** 4:3 photo well (fog-2), name at 17px, brand · model in slate, condition chip, fair price figure with range ruler, collapsible "Detalles de la tasación", then a paper secondary button plus a circular overflow menu.

### Inputs / Fields
- **Style:** paper background, hairline border, inner radius, 44px tall, 14px side padding, 15px text; labels sit 6px above.
- **Focus:** border shifts to accent, plus the global accent focus outline.

### Navigation
- **Top bar:** wordmark (accent rounded-square tag icon + Funnel Display "SmartLoot"), centred tab track, account pill (avatar + first name) that opens a menu.
- **Tabs:** fog pill track with 4px padding; tabs are 40px pills in slate control text; the active tab is a paper pill with accent text and the tab-lift shadow.
- **Menu:** 256px paper panel, inner radius, hairline ring, popover shadow; items are 15px medium with 18px icons, hover fog, destructive items in danger rose.

### Movement Row (signature)
The valuation-as-transaction row. A 44px paper icon disc with the category's lucide icon, name (semibold, up to 2 lines) over "time · condition · status" in slate, and on the right the fair price over its range. Rows are grouped under day labels (14px medium slate) and become paper on hover. A newly arrived row shows "+amount" in accent and enters with the arrive animation.

### Range Ruler (signature)
A 6px track (fog-2, or white/25 on accent) filled up to the fair price (accent/30, or white/55), a 3px accent marker (white on accent) at the fair price's true position, and "Venta rápida" / "Máximo" amounts at either end. Used for the total patrimony and every item; never replaced by three equal price tiles.

### Motion
- **Balance roll:** when the total changes, the figure rolls from old to new over 900ms with an exponential ease-out; a polite live region announces the final value. Instant under reduced motion.
- **Row arrive:** 1.4s `cubic-bezier(0.16, 1, 0.3, 1)` from 6px above with an emerald-wash tint that fades out. Disabled under reduced motion.
- **State transitions:** color transitions on hover; disclosure chevrons rotate 180deg when open.

## Do's and Don'ts

### Do:
- **Do** keep the accent (#0b6b3a) to one filled field per screen plus signals: primary button, active tab, arriving amount, focus.
- **Do** separate surfaces with tone: fog (#eef0f3) panels on paper, paper discs and buttons inside fog.
- **Do** show every price as a horquilla: venta rápida to máximo with the fair price marked on a range ruler.
- **Do** set all euro amounts in tabular figures and right-align them in lists.
- **Do** use pills for controls and tags, 20px for outer containers and 12px for inner surfaces.
- **Do** label placeholder content honestly ("Foto de ejemplo", "Ejemplo").
- **Do** honor reduced motion for the balance roll and row arrival.

### Don't:
- **Don't** introduce a second accent or a gradient; emerald is the only brand color.
- **Don't** use amber or rose for anything except value-losing conditions and destructive actions.
- **Don't** build a bento of equal stat tiles or a wall of photo cards on Inicio; photos live in Mi inventario.
- **Don't** add borders or shadows to panels at rest; shadows are for floating layers only.
- **Don't** add a dark theme; the product is light mode only for the projection room.
- **Don't** set body copy, buttons or labels in Funnel Display.
