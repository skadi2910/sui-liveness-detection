# Design System Specification: The Sovereign Manuscript

## 1. Overview & Creative North Star
**Creative North Star: The Sovereign Manuscript**

This design system is a high-end editorial interpretation of command-line authority. It rejects the "app-like" clutter of standard SaaS interfaces in favor of a sophisticated, tactile experience that feels like a digital technical manual printed on premium paper. By merging the brutalist efficiency of a terminal with the spaciousness of luxury print, we create an environment of absolute clarity and sovereign control.

The system breaks the "standard template" look through **intentional asymmetry**. We do not center everything; we use the monospaced grid to create purposeful "weighted" layouts where information is clustered to create focal points, balanced by expansive, breathing white space. Elements should feel "placed" on a surface rather than "caged" by borders.

## 2. Colors & Surface Philosophy
The palette is rooted in a high-readability, off-white environment that mimics the texture of architectural vellum or fine-grain paper.

*   **Core Tones:**
    *   **Background (#f9f9f9):** The "Paper" foundation. It is never pure white, providing a softer, more premium optical experience.
    *   **Primary (#0041c8):** The "Cyber Blue" accent. Used for high-priority actions and brand-critical indicators.
    *   **Secondary (#016e00):** The "Terminal Green." Reserved for success states, secondary data streams, and active terminal processes.
    *   **Surface Tiers:** Use `surface_container_low` (#f3f3f3) for the main workspace and `surface_container_highest` (#e2e2e2) for navigation or utility sidebars.

### The "No-Line" Rule
Standard 1px borders are strictly prohibited for sectioning. Boundaries must be defined solely through:
1.  **Background Color Shifts:** Placing a `surface_container_low` element against a `surface` background.
2.  **Negative Space:** Using the spacing scale to create "invisible" gutters that separate content blocks.

### The Glass & Gradient Rule
To prevent the UI from feeling "flat" or "cheap," floating elements (like modals or dropdowns) should utilize **Glassmorphism**. Use a semi-transparent version of `surface` with a `backdrop-blur` of 12px-20px. 
*   **Signature Textures:** Apply a subtle linear gradient from `primary` (#0041c8) to `primary_container` (#0055ff) on primary buttons to provide a "lit from within" glow that feels high-end and intentional.

## 3. Typography: The Monospace Rhythm
We utilize **Space Grotesk** as a monospaced-inspired system font. The fixed-width rhythm communicates precision, while the typeface's geometric construction ensures an editorial feel.

*   **Display (L/M/S):** Used for large data points or section titles. Use `display-lg` (3.5rem) with reduced letter-spacing (-0.02em) to create an authoritative, "stamped" look.
*   **Headline & Title:** Use for page headers. Always left-aligned to emphasize the "Manuscript" grid.
*   **Body (L/M/S):** The workhorse for data and prose. Ensure ample line-height (1.5x) to maintain readability on the light gray background.
*   **Labels:** Use `label-sm` (0.6875rem) in all-caps with increased letter-spacing (+0.1em) for metadata and terminal timestamps. This creates a high-contrast hierarchy between "Content" and "Data."

## 4. Elevation & Depth: Tonal Layering
In this design system, depth is a matter of "stacking sheets," not "casting shadows."

*   **The Layering Principle:** Physicality is achieved by nesting. A `surface_container_lowest` card should sit atop a `surface_container_low` section. This subtle 2-bit shift in gray value creates a sophisticated lift that feels integrated into the interface.
*   **Ambient Shadows:** Traditional drop shadows are replaced by "Ambient Occlusion." If an element must float, use a shadow with a 32px blur, 0px offset, and 6% opacity using the `on_surface` color. This mimics the soft, natural shadow of paper on a desk.
*   **The Ghost Border Fallback:** If a container requires a boundary for accessibility (e.g., an input field), use a "Ghost Border": the `outline_variant` token at 15% opacity. It should be barely visible—a suggestion of a boundary, not a cage.

## 5. Components

### Buttons
*   **Primary:** Solid `primary` background, `on_primary` text. No border. Soft `DEFAULT` (0.25rem) corner radius.
*   **Secondary:** `surface_container_high` background. Text in `primary`. These should feel like part of the background until hovered.
*   **Tertiary:** No background. Text in `primary` with an underline that only appears on hover.

### Input Fields
*   **Styling:** Forgo the "box." Use a `surface_container_low` background with a `surface_variant` bottom-weighted indicator (2px height).
*   **State:** On focus, the bottom indicator shifts to `primary` (#0041c8).

### Cards & Lists
*   **Rule:** No dividers. Separate list items using 12px of vertical white space or by alternating background tones between `surface` and `surface_container_lowest`.
*   **Header:** Use `label-sm` metadata headers to categorize list content, creating a technical, "cataloged" aesthetic.

### Additional Component: The "Terminal Status Bar"
A persistent `surface_container_highest` bar at the bottom or top of the viewport. It displays system health, timestamps, and active "Sovereign" processes using `label-sm` typography and `secondary` (green) accents.

## 6. Do's and Don'ts

### Do
*   **DO** use whitespace as a functional element. Treat empty space as a luxury.
*   **DO** align text to a strict monospaced grid. Elements should feel "snapped" into place.
*   **DO** use `tertiary` (#972500) for destructive actions or critical alerts to provide high-contrast warnings against the cool blue/green primary tones.

### Don't
*   **DON'T** use 100% black text. Always use `on_surface` (#1a1c1c) for a softer, more professional contrast.
*   **DON'T** use rounded corners larger than `lg` (0.5rem). The system should feel sharp, precise, and architectural.
*   **DON'T** use standard icons. Use glyphs that feel like terminal characters or simplified geometric shapes.