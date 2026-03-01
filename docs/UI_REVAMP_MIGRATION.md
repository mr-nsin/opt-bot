# QuantDrift UI Revamp — Futuristic Design Migration Plan

## Overview
Revamp the QuantDrift UI to match a modern, futuristic trading dashboard aesthetic (Crypto Link–style) while **keeping all functionality identical**.

## Scope
- **In scope:** Typography, colors, spacing, borders, shadows, visual effects, component styling
- **Out of scope:** Logic, routing, state management, APIs, trading behavior

---

## Phase 1: Typography

| Current | Target |
|---------|--------|
| Inter (body), JetBrains Mono (numbers) | **Plus Jakarta Sans** (body) — modern, geometric, excellent readability |
| Base 15px, many 9–11px labels | Base **16px**, labels **13–14px**, headings **15–18px** |
| Low contrast (`/50`, `/40` opacity) | Higher contrast: labels **85–95%** opacity, secondary **70%** |

**Files:** `index.html` (font import), `tailwind.config.js` (fontFamily), `src/index.css` (base body)

---

## Phase 2: Design Tokens (CSS Variables)

| Token | Current | Target |
|-------|---------|--------|
| `--radius` | 0.5rem | **0.75rem** (more rounded, futuristic) |
| Sidebar | Dark gray | Slightly lighter base, **blue glow** on active |
| Primary (blue) | 199 89% 48% | **217 91% 60%** (vibrant blue like reference) |
| Card backgrounds | `230 24% 9%` | Layered: card `230 22% 11%`, elevated `230 20% 13%` |
| Border opacity | 0.3–0.5 | **0.15–0.25** (subtler, cleaner) |

**Files:** `src/index.css` (`:root`, `.dark`)

---

## Phase 3: Sidebar — Futuristic Active State

- **Active nav item:** Blue glow background (`bg-primary/12` + `box-shadow: 0 0 20px primary/20`), rounded-lg
- **Glassmorphism:** Slight `backdrop-blur` on active item
- **Brand logo:** Larger, with subtle gradient ring
- **Icons:** 20px, white/primary for active
- **Badges:** Pill-shaped, red for errors, blue for PRO-like

**Files:** `Sidebar.tsx`, `index.css` (sidebar-pro)

---

## Phase 4: Cards & Surfaces

- **Card radius:** `rounded-xl` (12px) or `rounded-2xl` (16px)
- **Card shadow:** Softer, `0 1px 3px rgba(0,0,0,0.12)`, no harsh borders
- **Input radius:** `rounded-xl`
- **Button radius:** `rounded-xl`

**Files:** `card.tsx`, `input.tsx`, `button.tsx`, `StatCard`, dashboard cards

---

## Phase 5: Header & Layout

- **Header:** Taller (52px), cleaner separators, larger status text
- **Tabs:** Pill-style, larger text, clear active state
- **Spacing:** Increase `p-3` → `p-4` where appropriate

**Files:** `Header.tsx`, `tabs.tsx`, `AppShell.tsx`, `DashboardPage.tsx`

---

## Phase 6: Component Polish

- **StatCard:** Larger labels, cleaner icon containers, subtle inner glow
- **Buttons:** Consistent h-10 or h-11, font-semibold
- **Badges:** Pill-shaped, readable text
- **Progress bars:** Rounded, gradient fills for P&L

**Files:** All dashboard components, `ui/*`

---

## Implementation Order
1. Typography + tokens (index.html, tailwind, index.css)
2. Sidebar (Sidebar.tsx)
3. UI primitives (card, button, input)
4. Header, tabs, AppShell
5. Dashboard components (StatCard, RiskManagement, AccountSummary, etc.)

---

## Implementation Status ✓ (Screenshot-Exact Match)
- **Colors:** Background `#1A1A1A`, cards `#262626`, primary text `#E0E0E0`, muted `#A0A0A0` — applied in `.dark` theme.
- **Typography:** Plus Jakarta Sans; section titles 24px (`text-2xl`), key values 20–28px (`text-xl`/`text-2xl`), labels 14px (`text-sm`), detail 12px (`text-xs`).
- **Components:** Cards `rounded-2xl`, sidebar active glow, pill badges, large tab triggers.
- **Default:** Dark theme and `class="dark"` on `<html>` for immediate load.

## Rollback
All changes are CSS/styling only. Revert commits or restore `index.css`, `tailwind.config.js`, and component `className` changes to roll back.
