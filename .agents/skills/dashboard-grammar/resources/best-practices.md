# Best Practices described in Dashboard Grammar

## 1. Summary to Detail (The Inverted Pyramid)

> **UX Principle:** Users should see high-level KPIs first, trend contexts second, and granular tables last to avoid information overload.

### Grammar Expression

- **Composition Layer:** Enforce a strict Top-to-Bottom **V-Concat** hierarchy for the layout root.

  $$\text{Layout Root} = \text{V-Concat}(\text{Row}_1, \text{Row}_2, \text{Row}_3)$$

  - $\text{Row}_1$ (Immediate focus): **H-Concat** of `Value Card / KPI` primitives only.
  - $\text{Row}_2$ (Contextual focus): **H-Concat** of `Graphic` primitives.
  - $\text{Row}_3$ (Granular focus): `Tabular` primitive.

- **Linkage & Interaction Layer:** Limit the data volume flowing into top-tier rows.

  - `Value Card` targets must only accept heavily aggregated scalar inputs from the **Data State Layer** (e.g., `Aggregate: Sum`). They are strictly forbidden from receiving unaggregated arrays.

## 2. Progressive Disclosure

> **UX Principle:** Hide complex configurations or secondary views until the user explicitly requests them, keeping the primary workspace clean.

### Grammar Expression

- **Composition Layer:** Utilize a nested **Z-Concat** (Multiplex) or conditional **Overlay** for dense configurations.
  - The primary view workspace is a **Z-Concat** driven by a structural `Control` primitive (like a toggle or filter tray trigger).
- **Linkage & Interaction Layer:**
  - **Signal:** `Config_Panel_Visibility` (Boolean: True/False).
  - **Trigger:** Click on `Control` primitive (e.g., Hamburger icon).
  - **Target:** Composition Layer (Z-Concat / Overlay wrapper).
  - **Action:** Modify layout state to render the hidden filter pane overlay *without* altering the underlying **Data State Layer** until a secondary execution trigger occurs.

## 3. High Context-Switch Awareness (Preventing "Where am I?")

> **UX Principle:** When a user interacts with a chart, they should immediately see how it filters the rest of the dashboard, preserving the context of their analytical journey.

### Grammar Expression

- **Linkage & Interaction Layer (The Global Ripple):** Every interactive `Graphic` or `Tabular` component must broadcast a global signal upon selection.
  - **Signal:** `Active_Selection_Context` (tuples of `Dimension: Value`).
  - **Trigger:** Interaction (Click, Brush) on any coordinate mark in `Graphic A`.
  - **Targets:** *All* peer elements in the active composition container.
  - **Actions (Dual Delivery):**
    1. **Data State Layer Target:** Apply `Filter` transformation based on the signal tuple to recalculate values for all dependent components.
    2. **Encoding Layer Target:** If a peer component contains matching nominal dimensions, retain full opacity for matching `Marks` and drop non-matching `Marks` to `Opacity = 0.2` (Highlighting instead of hard-filtering).

## 4. Limit Visual Complexity (Miller’s Law / Hick's Law)

> **UX Principle:** A user can only process a handful of distinct choices or categorical items at once before decision paralysis sets in.

### Grammar Expression

- **Data State Layer (Hard-Bounded Arrays):**

  - Any categorical dimension fed into a nominal graphic axis *must* have an explicit `Transform: Top N Limit` applied by default (where $N \le 7$).
  - Remaining items must be grouped dynamically via `Transform: Aggregate (Sum)` into an `"Other"` category string.

- **Composition Layer (Strict Facet Bounds):**

  - If using a **Facet (Small Multiples)** operator, the data-driven replication must include an upper structural bound:

    $$\text{Facet}(\text{Graphic}, \text{Dimension}) \quad \text{where} \quad |\text{Unique}(\text{Dimension})| \le 5$$

  - If the unique cardinality of the slicing dimension exceeds 5, the grammar forces a **Z-Concat (Tabs)** composition instead of a spatial **H-Concat/V-Concat Facet**.

## 5. Preventing "No Data" Dead Ends

> **UX Principle:** If a user selects a combination of filters that returns zero records, the dashboard shouldn't break or display a confusing blank void.

### Grammar Expression

- **Data State Layer (Empty State Fallbacks):**

  - Introduce a conditional state evaluator on the Input stream:

    $$\text{If} \quad |\text{Data State}| = 0 \quad \text{then} \quad \text{State} = \text{Fallback\_Static\_Set}$$

- **Component Layer:**

  - An implicit structural `Value/Text Card` primitive is registered in an **Overlay** container directly over all primary graphics.

- **Linkage & Interaction Layer:**

  - **Signal:** `Is_Data_Empty` (Boolean).
  - **Trigger:** Calculation completion in the Data State Layer.
  - **Target:** The Overlay container.
  - **Action:** Set `Graphic Mark Opacity = 0` and `Fallback Text Card Opacity = 1`, displaying an explicit system status string (e.g., *"No records found matching current criteria"*).