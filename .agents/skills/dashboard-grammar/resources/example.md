# Example Dashboard



## SVG

```svg
<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
  <rect width="800" height="600" fill="#f4f6f8" />

  <rect x="0" y="0" width="160" height="600" fill="#2c3e50" />
  <text x="20" y="40" fill="#ffffff" font-family="sans-serif" font-weight="bold" font-size="16">Navigation</text>
  <text x="20" y="80" fill="#ffffff" font-family="sans-serif" font-size="14">Homepage</text>
  <rect x="10" y="105" width="140" height="30" fill="#34495e" rx="4" />
  <text x="20" y="125" fill="#4db8ff" font-family="sans-serif" font-weight="bold" font-size="14">Top Webpages</text>
  <text x="20" y="170" fill="#ffffff" font-family="sans-serif" font-size="14">Top Referrals</text>
  <text x="20" y="215" fill="#ffffff" font-family="sans-serif" font-size="14">Top Countries</text>

  <rect x="160" y="0" width="640" height="60" fill="#ffffff" stroke="#e0e0e0" />
  <text x="180" y="36" fill="#333333" font-family="sans-serif" font-weight="bold" font-size="18">[=] Web Traffic Dashboard</text>
  <rect x="620" y="15" width="160" height="30" fill="#f0f0f0" rx="4" />
  <text x="630" y="35" fill="#555555" font-family="sans-serif" font-size="12">Total | YTD | MTD</text>

  <rect x="180" y="80" width="190" height="70" fill="#ffffff" stroke="#e0e0e0" rx="4" />
  <text x="195" y="105" fill="#888888" font-family="sans-serif" font-size="12">Total Sessions</text>
  <text x="195" y="135" fill="#2c3e50" font-family="sans-serif" font-weight="bold" font-size="24">124,500</text>

  <rect x="385" y="80" width="190" height="70" fill="#ffffff" stroke="#e0e0e0" rx="4" />
  <text x="400" y="105" fill="#888888" font-family="sans-serif" font-size="12">Total Users</text>
  <text x="400" y="135" fill="#2c3e50" font-family="sans-serif" font-weight="bold" font-size="24">89,200</text>

  <rect x="590" y="80" width="190" height="70" fill="#ffffff" stroke="#e0e0e0" rx="4" />
  <text x="605" y="105" fill="#888888" font-family="sans-serif" font-size="12">Pageviews</text>
  <text x="605" y="135" fill="#2c3e50" font-family="sans-serif" font-weight="bold" font-size="24">342,100</text>

  <rect x="180" y="170" width="395" height="200" fill="#ffffff" stroke="#e0e0e0" rx="4" />
  <text x="195" y="195" fill="#555555" font-family="sans-serif" font-weight="bold" font-size="14">Traffic Trend</text>
  <polyline points="195,340 250,280 300,310 360,220 420,260 480,240 540,290" fill="none" stroke="#4db8ff" stroke-width="3" />
  <rect x="590" y="170" width="190" height="200" fill="#ffffff" stroke="#e0e0e0" rx="4" />
  <text x="605" y="195" fill="#555555" font-family="sans-serif" font-weight="bold" font-size="14">Top 10 Rank</text>
  <rect x="605" y="220" width="140" height="15" fill="#4db8ff" />
  <rect x="605" y="245" width="110" height="15" fill="#a0d8ff" />
  <rect x="605" y="270" width="85" height="15" fill="#a0d8ff" />
  <rect x="605" y="295" width="60" height="15" fill="#a0d8ff" />
  <rect x="605" y="320" width="40" height="15" fill="#a0d8ff" />

  <rect x="180" y="390" width="600" height="190" fill="#ffffff" stroke="#e0e0e0" rx="4" />
  <text x="195" y="415" fill="#555555" font-family="sans-serif" font-weight="bold" font-size="14">Dimension Detail Table</text>
  <line x1="180" y1="430" x2="780" y2="430" stroke="#e0e0e0" stroke-width="1" />
  <text x="195" y="450" fill="#888888" font-family="sans-serif" font-size="12">Webpage Path</text>
  <text x="450" y="450" fill="#888888" font-family="sans-serif" font-size="12">Sessions</text>
  <text x="600" y="450" fill="#888888" font-family="sans-serif" font-size="12">% of Total</text>
  <line x1="180" y1="460" x2="780" y2="460" stroke="#e0e0e0" stroke-width="1" />
  <text x="195" y="485" fill="#333333" font-family="sans-serif" font-size="12">/home</text>
  <text x="450" y="485" fill="#333333" font-family="sans-serif" font-size="12">45,210</text>
  <text x="600" y="485" fill="#333333" font-family="sans-serif" font-size="12">36%</text>

  <text x="195" y="515" fill="#333333" font-family="sans-serif" font-size="12">/products/shoes</text>
  <text x="450" y="515" fill="#333333" font-family="sans-serif" font-size="12">28,100</text>
  <text x="600" y="515" fill="#333333" font-family="sans-serif" font-size="12">22%</text>

  <text x="195" y="545" fill="#333333" font-family="sans-serif" font-size="12">/about-us</text>
  <text x="450" y="545" fill="#333333" font-family="sans-serif" font-size="12">15,050</text>
  <text x="600" y="545" fill="#333333" font-family="sans-serif" font-size="12">12%</text>
</svg>

```



## ASCII

```
+-----------------------------------------------------------------------------+
| [=] Filters      |  Web Traffic Dashboard               | [Total][YTD][MTD] |
+------------------+----------------------------------------------------------+
|                  |                                                          |
| > Homepage       |  [ KPI: Sessions ] [ KPI: Users ] [ KPI: Pageviews ]     |
|                  |                                                          |
| > Top Webpages   |  +--------------------------------+  +-----------------+ |
|   (ACTIVE)       |  | Trend_Plot                     |  | Top_10_Rank     | |
|                  |  | (X: Time, Y: Sessions)         |  |                 | |
| > Top Referrals  |  |           /\                   |  | Item A [=====]  | |
|                  |  |      /\/\/  \                  |  | Item B [====]   | |
| > Top Countries  |  |     /        \/\               |  | Item C [==]     | |
|                  |  |    /            \              |  | Item D [=]      | |
|                  |  +--------------------------------+  +-----------------+ |
|                  |                                                          |
|                  |  +-----------------------------------------------------+ |
|                  |  | Dimension_Detail_Table                              | |
|                  |  | Dimension    | Metric 1 (Sess)  | Metric 2 (Views)  | |
|                  |  |-----------------------------------------------------| |
|                  |  | Webpage A    | 12,345           | 24,500            | |
|                  |  +-----------------------------------------------------+ |
+------------------+----------------------------------------------------------+
```



## Description in Dashboard Grammar

The Web Traffic Dashboard (Described via Dashboard Grammar)

1. Data State Layer (Inputs & Transformations)

Base Data: Web traffic event logs (Sessions, Pageviews, Referrals, Geography, Device).

Transformations:

Global Filter: Filter out/in data by Country, Traffic Type, and Device Category.

Temporal Aggregation: Time boundaries grouped dynamically by "Total", "Year-to-Date" (YTD), or "Month-to-Date" (MTD).

View-Specific Aggregation: Top 10 Limit applied to dimensions (Webpages, Referral Sites, or Countries) depending on the active route.

2. Component Layer (The Primitives)

Navigation: Left-hand sidebar tabs (Homepage, Top 10 Webpages, Top 10 Referral Sites, Top 10 Countries).

Control A (Temporal Toggle): Horizontal button group (Total, YTD, MTD).

Control B (Global Filters): A collapsible/overlay menu pane (triggered by a hamburger icon) containing dropdowns.

Value Card: Top-row KPI blocks (e.g., Total Sessions, Pageviews).

Graphic A (Trend_Plot): Time-series chart showing traffic over time.

Graphic B (Top_10_Rank_Plot): A categorical ranking chart.

Tabular (Dimension_Detail_Table): A granular data grid listing individual web pages, referrers, or countries and their associated metrics.

3. Encoding Layer (For Graphic Components)

Graphic A (Trend_Plot):

Mark: Line or Area.

Positional Channels: X-axis = Time (Continuous Date), Y-axis = Primary KPI (Quantitative, e.g., Sessions).

Graphic B (Top_10_Rank_Plot):

Mark: Bar.

Positional Channels: X-axis = Metric Value (Quantitative), Y-axis = Dimension (Nominal, e.g., Country or Webpage).

4. Composition Layer (Spatial Layout)

Root R-Concat (Main Dashboard Split):

Sector 1 (Left Sidebar): Contains the Navigation component.

Sector 2 (Main Canvas): Driven by the global top-bar and Z-Concat.

Main Canvas Top-Bar (H-Concat): Control A (Time Toggle) + Control B (Hamburger Filter trigger).

Z-Concat (Content Area): Multiplexed views based on Navigation state (switching between Homepage_Layout and Top_10_Analysis_Layout).

Top_10_Analysis_Layout (V-Concat):

Row 1 (H-Concat): Facet of KPI Value Cards.

Row 2 (H-Concat): Trend_Plot placed alongside the Top_10_Rank_Plot.

Row 3: Tabular (Dimension_Detail_Table).

5. Linkage & Interaction Layer (The Wiring)

Linkage 1 (Page Routing):

Signal: Active_Page.

Trigger: Click on Left Sidebar Navigation tabs.

Target: Z-Concat (Content Area) & Data State Layer.

Action: Switches visible layout (e.g., bringing the "Top 10 Countries" layout to the front) and sets the grouping dimension for the Tabular and Rank plots.

Linkage 2 (Time Aggregation):

Signal: Time_Window_Selection.

Trigger: Click on Control A (Total, YTD, MTD).

Target: Data State Layer.

Action: Recalculates the time bounding box for all KPIs, Encodings, and Top 10 rankings on the visible screen.

Linkage 3 (Global Filtering):

Signal: Filter_State.

Trigger: Selections made inside Control B (Hamburger menu).

Target: Data State Layer.

Action: Excludes non-matching rows from the Base Data feeding all visible components.

Linkage 4 (Cross-Filtering / Deep Dive):

Signal: Selected_Dimension_Item.

Trigger: Click on a specific row inside the Tabular component or a specific bar in Top_10_Rank_Plot.

Target: All other Graphic and Value Card components in the visible Z-Concat.

Action: Filters the Data State feeding the Trend_Plot and KPI cards to reflect only the specific webpage/country/referral clicked by the user. 