**Style rules for agricultural wholesale price dashboard**

**1. Overall visual character**

The product should feel like a serious public market-data tool: analytical, readable, and business-oriented. It should have some commodity-market character, but without becoming rustic, nostalgic, decorative, or “farm themed”.

The target mood is:

modern public-data brief + commodity market sheet + restrained analytical interface.

It should not feel like:

- high-frequency trading software,
- a high-tech control room,
- a generic SaaS analytics dashboard,
- a farming lifestyle page,
- an LLM-generated “earth tones agriculture” mockup,
- a newspaper replica,
- a decorative report.

The style should be recognizable mostly through typography, alignment, color discipline, and crisp construction.

**2. Typography**

Use neutral, functional sans-serif typography.

Preferred direction:

font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;

Typography should be clean, compact, and public-data oriented. It should not look editorial, ornamental, techy, or trendy.

Use tabular numerals for all numeric values:

font-variant-numeric: tabular-nums;

**Typography rules**

Use:

- one primary sans-serif family,
- strong but restrained heading weights,
- compact uppercase metadata labels,
- tabular numbers,
- clear hierarchy through size, weight, spacing, and alignment,
- slightly tight tracking for large titles if useful.

Avoid:

- decorative serifs,
- nostalgic newspaper typography,
- monospace as the main visual identity,
- playful rounded fonts,
- condensed “terminal” styling,
- too many typefaces,
- overly light gray text that hurts readability.

Typography should carry authority without shouting.

**3. Color direction**

Use a mostly neutral interface with a controlled warm market-bulletin palette.

The page background should be near-white or very pale neutral. Do not use a beige full-page background.

Agricultural/commodity character should come from accents and data colors, not from washing the whole UI in earth tones.

**Suggested palette family**

--bg: #fcfcfb;    /* near-white background */

--surface: #ffffff;  /* main surfaces */

--ink: #171511;    /* primary text */

--muted: #6e6a61;   /* secondary text */

--rule: #d8d3ca;   /* borders/dividers */

--soft: #f3f1ed;   /* subtle neutral fill */

 

--green: #396b51;   /* primary crop/market accent */

--green-soft: #d8e1d7;

 

--rust: #a9683d;   /* comparison / warm market accent */

--rust-soft: #ead6c6;

 

--blue: #2c4f6e;   /* cool secondary accent */

--blue-soft: #e1e9ef;

 

--missing: #b0a89c;  /* unavailable/missing data */

The exact palette can evolve, but it should stay within this family: warm-neutral, muted green, rust, restrained blue, charcoal ink.

**Color rules**

Use color as meaning, not decoration.

Color should identify roles such as:

- primary/current data,
- comparison data,
- secondary reference data,
- missing/unavailable state,
- structural emphasis,
- muted supporting information.

Avoid:

- gradients,
- neon colors,
- saturated red/green “trading app” semantics,
- full beige or brown page backgrounds,
- random per-card colors,
- excessive palette mixing,
- decorative color blocks with no information purpose.

The color system should feel calm, deliberate, and stable.

**4. Shape language**

Use sharp, rectangular geometry.

This is a strong requirement.

border-radius: 0;

box-shadow: none;

Surfaces, controls, panels, tables, chart frames, buttons, and chips should generally have square corners.

**Shape rules**

Use:

- straight edges,
- crisp borders,
- thin rules,
- rectangular fields,
- rectangular buttons,
- structured alignment.

Avoid:

- rounded cards,
- pill buttons,
- soft floating surfaces,
- drop shadows,
- glassmorphism,
- gradients,
- skeuomorphic paper texture,
- decorative organic shapes.

Sharp does not mean overly boxed. The layout should not become a grid of equal rectangles. Use rectangular construction, but let hierarchy come from size, spacing, rules, and typography.

**5. Borders and dividers**

Prefer borders and rules over shadows.

Use thin dividers for normal separation:

border: 1px solid var(--rule);

Use stronger rules only for major hierarchy:

border-top: 2px solid var(--ink);

or

border-bottom: 2px solid var(--ink);

**Border rules**

Use:

- thin, warm-gray borders,
- occasional dark structural rules,
- clear alignment to grid,
- table-like dividers.

Avoid:

- many nested boxes,
- heavy outlines everywhere,
- thick black borders on every element,
- shadow-based separation,
- decorative dashed lines unless indicating missing/unavailable data.

**6. Surface treatment**

Surfaces should be flat.

Use:

- white surfaces,
- very pale neutral fills,
- subtle warm-gray backgrounds for secondary zones,
- crisp boundaries.

Avoid:

- gradients,
- shadows,
- blur effects,
- transparent glass panels,
- image/textured backgrounds,
- large beige panels that dominate the page.

The design should feel closer to a well-made statistical bulletin than to a card-based SaaS dashboard.

**7. Spacing and density**

The interface should be information-dense but not cramped.

Agricultural prices are volatile and require context, so the style must support analytical reading rather than oversized KPI display.

**Spacing rules**

Use:

- generous space around major analytical areas,
- compact spacing inside labels, tables, and metadata,
- consistent grid rhythm,
- strong vertical grouping.

Avoid:

- huge whitespace that makes the dashboard feel like a landing page,
- dense terminal-like compression,
- oversized metric cards,
- equal-weight dashboard tiles,
- spacing that hides context below the fold unnecessarily.

The style should support scanning and detailed reading.

**8. Data visualization style**

Charts should look analytical, direct, and trustworthy.

Line charts are expected to be major working elements, so the visual style must support them well.

**Chart style rules**

Use:

- clean lines,
- visible but subtle gridlines,
- muted axis labels,
- direct legends,
- restrained color roles,
- clear distinction between current, comparison, and missing data,
- flat fills only if needed,
- no decorative chart effects.

Avoid:

- gradient fills under lines,
- glowing lines,
- animated decoration,
- tiny hover-only details as the primary reading mechanism,
- overly colorful multi-series spaghetti charts,
- hidden axes,
- chart junk,
- inferred “season phase” visual labels unless backed by data.

For volatile data, the style should encourage reading the shape over time, not judging isolated percent deltas.

**9. Numeric and tabular style**

Numbers should be visually precise.

Use:

- tabular numerals,
- aligned decimals where possible,
- clear units,
- compact labels,
- consistent sign formatting.

Example style principles:

+8,5%

−4,6%

12,40–15,80 zł/unit

Tables or table-like areas should feel crisp and public-data-like.

Use:

- clear row separation,
- subtle header fill,
- uppercase compact headers,
- aligned numeric columns,
- explicit missing states.

Avoid:

- colorful spreadsheet chaos,
- rounded table cells,
- excessive zebra striping,
- decorative icons in every row,
- hiding units.

**10. Missing and unavailable data**

Missing data should have its own quiet style.

Use:

- muted taupe/gray,
- explicit text,
- dashes for unavailable numbers,
- dashed or lighter treatment only when it clearly means unavailable.

Avoid:

- replacing missing data with zero,
- visually smoothing over gaps,
- making missing data look like an error or alert,
- bright warning colors for normal data absence.

The style should normalize missing weekly observations as part of the dataset reality.

**11. Interaction style**

The visual system should not depend on subtle hover interactions.

This is especially important for mobile.

**Interaction rules**

Use:

- visible labels,
- visible legends,
- visible values for important states,
- larger tap targets,
- simple rectangular controls.

Avoid:

- tooltip-only critical information,
- tiny clickable chart dots,
- hover-dependent explanations,
- swipe-heavy analysis,
- dense hidden menus for primary functions.

Interaction can reveal finer detail, but the default visual state must already communicate the main analytical context.

**12. Mobile style**

Mobile should preserve the same visual identity.

Do not create a completely different mobile aesthetic.

At small widths:

- typography should remain readable,
- hierarchy should remain clear,
- charts should remain useful,
- rectangular sharp style should remain,
- spacing should tighten but not collapse.

Avoid:

- tiny chart labels,
- hover-only values,
- huge cards that push analytical context away,
- hiding all detail behind accordions,
- making the mobile version only a summary-card feed.

**13. Thematic constraints**

Agricultural theme should be subtle.

Acceptable thematic cues:

- muted green/rust/ink palette,
- commodity-bulletin tone,
- price-sheet alignment,
- public-data styling,
- Polish market terminology,
- crisp weekly-report rhythm.

Unacceptable thematic cues:

- barns,
- fields,
- crop illustrations,
- vintage paper,
- rustic wood,
- excessive beige,
- decorative leaves,
- “organic” rounded blobs,
- nostalgic newspaper imitation.

The design should say “market data about agricultural goods”, not “farm brand”.

**14. Dark mode compatibility**

The primary theme is light.

However, color choices should be adaptable to dark mode later.

Do not rely on:

- low-contrast pale colors,
- beige backgrounds as identity,
- shadow depth,
- subtle gradients.

A future dark mode should be able to preserve:

- sharp rectangular geometry,
- warm market accents,
- tabular precision,
- chart-first clarity,
- muted comparison colors.

**15. Core design do/don’t summary**

**Do**

- Use neutral sans typography.
- Use tabular numerals.
- Use near-white background.
- Use warm market-bulletin accents.
- Use muted green, rust, blue, charcoal, warm gray.
- Use square corners.
- Use flat surfaces.
- Use borders and rules instead of shadows.
- Make line charts visually central when analytics are involved.
- Keep color semantic.
- Make important information visible without hover.
- Preserve missing data visibly.

**Don’t**

- Don’t use gradients.
- Don’t use rounded cards.
- Don’t use beige full-page background.
- Don’t use shadows as the main depth system.
- Don’t use rustic farm imagery.
- Don’t use decorative serifs or newspaper cosplay.
- Don’t make it look like a trading terminal.
- Don’t overuse KPI cards.
- Don’t infer recommendations through labels or visual metaphors.
- Don’t make all modules equal rectangular tiles.
- Don’t hide critical context in tooltips.

**16. One-sentence style target**

A sharp, flat, neutral-sans public market-data interface with warm commodity-bulletin accents, designed for analytical price reading rather than decorative agricultural branding.