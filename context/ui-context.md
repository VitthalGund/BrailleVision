# BrailleVision — UI Context & Design System

## Design Philosophy

- **Accessibility-first**: High contrast, large tap targets (min 44px), screen-reader compatible
- **Camera-centric**: The camera feed is the hero element — full-screen capable
- **Single-handed**: Mobile users may hold Braille material in one hand; all controls must be thumb-reachable
- **Calm and focused**: No visual noise during scanning; results appear cleanly below the feed

---

## Color Palette

### Primary Brand

| Name          | Hex       | Usage                       |
| ------------- | --------- | --------------------------- |
| Vision Blue   | `#1A56DB` | Primary CTA, active states  |
| Deep Navy     | `#1E2A3A` | Headers, dark mode bg       |
| Electric Teal | `#0891B2` | Accent, AI assistant bubble |
| Warm White    | `#F8FAFC` | App background (light mode) |

### Semantic

| Name          | Hex       | Usage                   |
| ------------- | --------- | ----------------------- |
| Success Green | `#10B981` | High-confidence cells   |
| Warning Amber | `#F59E0B` | Medium-confidence cells |
| Error Red     | `#EF4444` | Low-confidence / errors |
| Neutral Gray  | `#6B7280` | Muted text, borders     |

### Dark Mode Overrides

| Light          | Dark           |
| -------------- | -------------- |
| `#F8FAFC` bg   | `#0F1729` bg   |
| `#1E2A3A` text | `#E2E8F0` text |
| `#FFFFFF` card | `#1E2A3A` card |

---

## Typography

| Role            | Font       | Size | Weight |
| --------------- | ---------- | ---- | ------ |
| App title       | Inter      | 24px | 700    |
| Section heading | Inter      | 18px | 600    |
| Body text       | Inter      | 16px | 400    |
| Result text     | Inter Mono | 18px | 400    |
| Caption / label | Inter      | 13px | 400    |
| AI chat         | Inter      | 15px | 400    |

**Font loading**: Google Fonts CDN — Inter (400, 600, 700) + JetBrains Mono (400)

---

## Component Library

### CameraView

- Full-width card with 16:9 aspect ratio (or native camera ratio)
- Green overlay rectangle when scanning
- Confidence HUD overlaid (top-right corner): `87% ↑`
- Controls bar below: [Flash] [Rotate] [Capture] [Live Mode]

### ResultPanel

- Scrollable text area, monospace font for Braille output
- Character-level confidence coloring (green/amber/red bg highlight)
- Copy button (top-right), TTS play button
- Language selector dropdown (translate to any language)

### AIAssistant

- Slide-up bottom sheet on mobile, right sidebar on desktop
- Suggested prompts when empty: "What does ⠓ mean?", "Help me hold the paper"
- Chat bubbles: user right (blue), Claude left (teal)
- Always shows "powered by Claude" attribution

### NavBar

- Logo left + app name
- Icons: Camera | History | Settings | Help
- On mobile: bottom tab bar
- On desktop: left sidebar

### BrailleCellDebugger (judge demo feature)

- Toggle-able overlay on camera feed
- Shows bounding boxes around each detected Braille cell
- Shows dot positions with confidence scores
- Color-coded by character confidence

---

## Layout System

### Mobile (< 768px)

```
┌───────────────────┐
│    NavBar/Logo    │
├───────────────────┤
│                   │
│   Camera Feed     │
│   (full width)    │
│                   │
├───────────────────┤
│  Result Text      │
│  (scrollable)     │
├───────────────────┤
│  [TTS] [Copy] [⟳]│
├───────────────────┤
│ 📷 📜 ⚙️ ❓       │  ← bottom tabs
└───────────────────┘
```

### Desktop (≥ 1024px)

```
┌──────┬───────────────────────┬──────────────┐
│ Side │   Camera Feed          │  AI Assistant│
│ Nav  │   (main area)          │  (sidebar)   │
│      ├───────────────────────┤              │
│      │   Result Panel         │              │
│      │   (scrollable)         │              │
└──────┴───────────────────────┴──────────────┘
```

---

## Accessibility Requirements

- `role="img"` + `aria-label` on all camera canvas elements
- Live region (`aria-live="polite"`) on result text for screen reader announcement
- All buttons: visible focus ring, min 44×44px
- Color never the only indicator of state (always + icon or text)
- TTS enabled by default (toggle in settings)
- Reduced motion preference respected for animations

---

## Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "vision-blue": "#1A56DB",
        "deep-navy": "#1E2A3A",
        "electric-teal": "#0891B2",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
};
```
