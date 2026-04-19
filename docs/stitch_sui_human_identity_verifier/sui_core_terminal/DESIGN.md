# Design System Documentation: The Sovereign Console

## 1. Overview & Creative North Star
### Creative North Star: "The Sovereign Console"
This design system is a sophisticated evolution of the terminal aesthetic. It moves beyond "retro-computing" cliches to create an elite, high-integrity environment for identity verification. We are not building a toy; we are building a secure, developer-centric gateway. 

The system breaks the "standard web template" look by utilizing **Intentional Asymmetry**. By using a rigid 1px grid-base but staggering the placement of content blocks, we evoke the feeling of a custom-coded mainframe. Expect high-contrast typography scales, overlapping data modules, and a layout that breathes through technical precision rather than decorative white space.

---

## 2. Colors & Surface Architecture
Our palette is rooted in the high-contrast world of terminal outputs. It leverages the depth of charcoal and the vibrance of neon phosphor.

### Surface Hierarchy & Nesting
We do not use drop shadows to define space; we use **Tonal Layering**. Depth is achieved by stacking `surface-container` tiers.
*   **Base:** The main viewport uses `surface` (`#0e0e0e`).
*   **Nesting:** Place a `surface-container-low` (`#131313`) section to denote a secondary area. Inside that, use `surface-container-high` (`#201f1f`) for interactive modules.
*   **The "No-Line" Rule:** Prohibit 1px solid borders for sectioning layout. Boundaries must be defined solely through background color shifts. A transition from `surface` to `surface-container-lowest` is more "editorial" and premium than a hard line.

### Signature Textures & Glass
*   **The CRT Scanline:** Apply a subtle, fixed-position overlay with a repeating linear gradient to simulate the texture of a physical monitor. This provides "visual soul" to the flat dark surfaces.
*   **Glassmorphism:** For floating modals or "Head-Up Display" (HUD) elements, use `surface-variant` (`#262626`) at 60% opacity with a `20px` backdrop-blur. This makes the UI feel integrated into a singular, cohesive machine.
*   **CTA Gradients:** For primary actions, use a subtle gradient from `primary` (`#9cff93`) to `primary-container` (`#00fc40`). This adds a "glow" effect reminiscent of active phosphor.

---

## 3. Typography
The typography is a dialogue between human-readable editorial styles and machine-readable data.

*   **Display & Headlines (Space Grotesk):** Used for high-impact brand moments. These should feel brutalist and authoritative. Use `display-lg` (`3.5rem`) with tight letter-spacing (-0.02em) to command attention.
*   **The Monospace Core (JetBrains Mono / Fira Code):** All functional UI, labels, and data inputs must use high-quality monospace fonts. This reinforces the "Proof-of-Human" technical nature.
*   **Hierarchy:** 
    *   `title-lg`: Monospace, uppercase, `on-surface-variant`.
    *   `body-md`: Monospace, `on-surface`.
    *   `label-sm`: Monospace, `primary`, used for metadata and system status.

---

## 4. Elevation & Depth
In this system, elevation is an optical illusion created by light and tone, not physical shadows.

*   **The Layering Principle:** Stack `surface-container` tiers. For example, a "Human Verification" card should be `surface-container-highest` (`#262626`) sitting atop a `surface-dim` (`#0e0e0e`) background.
*   **Ambient Shadows:** If a floating element (like a tooltip) requires a shadow, use a "Tinted Glow." Instead of black, use `primary` at 10% opacity with a `40px` blur. It should look like the element is emitting light, not blocking it.
*   **The "Ghost Border" Fallback:** If a border is required for accessibility, use the `outline-variant` token at 15% opacity. Never use 100% opaque borders for containers; it breaks the "Sovereign Console" aesthetic.

---

## 5. Components

### Buttons (Blocky & Brutalist)
*   **Primary:** Background: `primary` (`#9cff93`), Text: `on-primary` (`#006413`). 0px border-radius.
*   **Secondary:** Border: 1px solid `primary`, Background: Transparent.
*   **States:** On hover, the primary button should "glitch" or shift to `primary-dim`. Use a `2px` offset shadow of the same color to simulate a 3D block.

### Input Fields (Command Line Style)
*   Forgo the traditional box. Use a bottom-only border (1px) of `outline`.
*   **Focus State:** The bottom border shifts to `primary` with a blinking underscore cursor.
*   **Error State:** Use `error` (`#ff7351`) for the border and helper text.

### Cards & Data Modules
*   **Constraint:** Forbid the use of divider lines within cards.
*   **Separation:** Use `surface-container-highest` for header areas and `surface-container-low` for content bodies.
*   **The "Human Pulse" Component:** A specialized visualizer for identity verification status using a canvas-based waveform in `tertiary` (`#6ad6ff`).

### Checkboxes & Radios
*   Strictly square (0px radius). 
*   **Checked:** Solid `primary` block with a high-contrast `on-primary` "X" or "DOT".

---

## 6. Do’s and Don’ts

### Do:
*   **Do** use asymmetrical margins (e.g., 80px left, 120px right) to create an "engineered" feel.
*   **Do** use `label-sm` for "System Metadata" (e.g., "LATENCY: 24ms", "STATUS: VERIFIED") in the corners of sections.
*   **Do** embrace the 0px radius. Every corner must be sharp enough to cut.

### Don’t:
*   **Don’t** use rounded corners (`border-radius: 0 !important`).
*   **Don’t** use standard "Web 2.0" blue for links. Use `tertiary` (`#6ad6ff`) or `primary`.
*   **Don’t** use 1px solid borders to separate main layout sections. Use background color shifts (`surface` vs `surface-container`).
*   **Don’t** use generic transitions. Use "Step" timing functions (e.g., `steps(4)`) for animations to mimic terminal refresh rates.