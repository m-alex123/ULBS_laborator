# DESIGN — Design Tokens & UI Guidelines (P23 Sneaker Price Monitor)

<!-- graffino-agentic:begin v1 -->
> Design system specification and token dictionary for the P23 Ethical Sneaker Price Monitor.
> Live market ticker aesthetic: high contrast, sharp geometry, flat 1px borders,
> pure functional typography, and zero generic gradients.
<!-- graffino-agentic:end -->

## 1. Aesthetic Direction & Principles

1. **P23 Live Market Aesthetic**: Clean, authoritative, and data-dense sneaker comparison platform. No unnecessary decorative fluff, rounded pill bubbles, or pastel purple accents.
2. **Sharp Geometry**: Radius is restricted to **2px–6px max** (`--radius-sm: 4px`, `--radius-md: 6px`). Cards and containers feature crisp 1px borders without heavy diffuse drop shadows.
3. **High-Contrast Palette**:
   - **Light Mode**: Pure white canvas (`#FFFFFF`), white cards with fine `#E5E5E5` borders, and `#F4F4F4` light gray product presentation panels.
   - **Dark Mode**: Matte carbon backdrop (`#0D0D0D`), deep charcoal cards (`#161616`), `#1F1F1F` secondary panels, and `#2A2A2A` borders.
4. **Signature Status & Financial Accents**:
   - **Emerald / Forest Green** (`#006340` Light / `#00A86B` Dark) represents „Cel mai mic preț”, price drops, in-stock confirmation, and scraper health.
   - **Exchange Red** (`#D92D20` Light / `#F04438` Dark) indicates price increases, adapter circuit breaker trips, and critical errors.
5. **Specialized Typography**:
   - Headlines and UI labels: `Inter` with tight tracking (`letter-spacing: -0.025em` to `-0.03em`), bold hierarchy.
   - Pricing, SKUs, and Tickers: `JetBrains Mono` with `font-feature-settings: "tnum" 1` for consistent numeric alignment.

---

## 2. Token Dictionary (CSS Custom Properties)

These variables are defined on `:root` (Light mode) and overridden under `[data-theme="dark"]`.

### 2.1. Color Tokens

| Token Name | Light Mode Value | Dark Mode Value | Usage / Semantic Role |
|---|---|---|---|
| `--color-bg-canvas` | `#FFFFFF` (pure white) | `#0D0D0D` (matte carbon) | Viewport and main canvas background |
| `--color-bg-surface` | `#FFFFFF` | `#161616` (charcoal) | Card and panel backgrounds |
| `--color-bg-secondary` | `#F4F4F4` (light gray) | `#1F1F1F` (secondary dark) | Sneaker image backdrop, ticker strip |
| `--color-bg-tertiary` | `#EAEAEA` | `#262626` | Inputs, hover rows, inactive chips |
| `--color-text-primary` | `#0D0D0D` (pitch black) | `#F5F5F5` (crisp white) | Brand, titles, lowest prices |
| `--color-text-secondary` | `#555555` | `#B3B3B3` | Metadata, SKU, store labels |
| `--color-text-muted` | `#666666` | `#8E8E8E` | Timestamps, table captions, hints (WCAG AA) |
| `--color-border-subtle` | `#EEEEEE` | `#222222` | Inner dividers, secondary borders |
| `--color-border-default` | `#E5E5E5` | `#2A2A2A` | Standard 1px card and table borders |
| `--color-border-strong` | `#CCCCCC` | `#404040` | Active controls, hover card borders |
| `--color-border-focus` | `#0D0D0D` | `#00A86B` | Keyboard focus ring (`:focus-visible`) |

### 2.2. Market Accent Tokens

| Token Name | Light Mode | Dark Mode | Role |
|---|---|---|---|
| `--color-ask-green` | `#006340` (Forest Green) | `#00A86B` (Vibrant Emerald) | Cel mai mic preț, discount badge, in-stock dot |
| `--color-ask-green-bg` | `#EBF7F2` | `#0E291E` | Cel mai mic preț pill background, healthy tag |
| `--color-ask-green-border`| `#BDE3D2` | `#17523C` | Cel mai mic preț border |
| `--color-loss-red` | `#D92D20` (Exchange Red) | `#F04438` | Price rise, circuit breaker alert, out-of-stock |
| `--color-loss-red-bg` | `#FEECEB` | `#331414` | Error banner background |
| `--color-loss-red-border`| `#FECDCA` | `#5D1F1F` | Error banner border |
| `--color-warning-amber` | `#B54708` | `#F79009` | Degraded adapter warning |
| `--color-warning-amber-bg`| `#FEF0C7` | `#332008` | Degraded adapter badge background |

### 2.3. Retailer Identity Tokens

| Retailer | Light Mode Tag | Dark Mode Tag |
|---|---|---|
| **JD Sports** (`jdsports.ro`) | `#001428` bg / `#FFFFFF` text | `#002244` bg / `#FFFFFF` text |
| **Sizeer** (`sizeer.ro`) | `#141414` bg / `#FACC15` text | `#262626` bg / `#FACC15` text |
| **Buzz Sneakers** (`buzzsneakers.ro`) | `#D92D20` bg / `#FFFFFF` text | `#7F1D1D` bg / `#FCA5A5` text |

---

## 3. Typography Tokens

```css
:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;

  /* Type Scale */
  --text-3xs: 0.625rem;  /* 10px - Micro ticker labels, store codes */
  --text-2xs: 0.6875rem; /* 11px - Badge labels, SKU headers */
  --text-xs: 0.75rem;     /* 12px - Metadata, timestamps, comparison rows */
  --text-sm: 0.875rem;    /* 14px - Body copy, buttons, table data */
  --text-base: 1rem;       /* 16px - Standard headings, inputs */
  --text-lg: 1.125rem;    /* 18px - Card product titles */
  --text-xl: 1.25rem;     /* 20px - Section titles */
  --text-2xl: 1.5rem;     /* 24px - Large Cel mai mic preț */
  --text-3xl: 2rem;       /* 32px - Ticker hero figures */

  /* Weights & Tracking */
  --font-regular: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
  --font-extrabold: 800;

  --tracking-tight: -0.025em;
  --tracking-tighter: -0.04em;
  --tracking-wide: 0.05em;
}
```

---

## 4. Geometry, Spacing & Shadows

```css
:root {
  /* Sharp Geometry: 2px to 6px maximum */
  --radius-xs: 2px;
  --radius-sm: 4px; /* Badges, inputs, buttons */
  --radius-md: 6px; /* Cards, modals */
  --radius-none: 0px;

  /* 4px Rhythm Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;

  /* Flat / Minimal Shadows */
  --shadow-none: none;
  --shadow-subtle: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
  --shadow-card: 0 1px 3px 0 rgba(0, 0, 0, 0.06);
}
```

---

## 5. P23 Sneaker Card Anatomy

1. **Card Frame**: 1px flat border (`var(--color-border-default)`), sharp 6px radius (`var(--radius-md)`), background `var(--color-bg-surface)`.
2. **Visual Area**: 200px fixed height box on neutral presentation background (`#F4F4F4` Light / `#1F1F1F` Dark) displaying real HTTPS product photography (`object-fit: contain`, `mix-blend-mode: multiply` in Light mode, framed `#FFFFFF` stage in Dark mode), retailer attribution badge, photo source badge, and clean offline SVG fallback.
3. **Market Metrics**:
   - Label: `CEL MAI MIC PREȚ` in uppercase 10px tracking.
   - Price: Bold `font-mono` in `var(--color-text-primary)` (e.g., `489.99 RON`).
   - Sparkline SVG: 7-point mini trend line visualising 30-day price movement.
4. **Multi-Store Ticker Table**: Compact 3-row grid comparing `jdsports.ro`, `sizeer.ro`, `buzzsneakers.ro` with active store tag and lowest price green badge.
5. **Title Resiliency**: 2-line clamping (`line-height: 1.25rem; min-height: 2.5rem; max-height: 2.5rem`) with `title` tooltip preventing vertical card misalignment and line-3 bleed.
