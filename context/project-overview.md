# BrailleVision — Project Overview

## One-Line Problem Statement

Blind and visually impaired people cannot independently read physical Braille documents without another Braille-literate person nearby — BrailleVision fixes this with a camera-based real-time Braille-to-text-and-speech converter that works in any language, on any device.

## Product Name

**BrailleVision** — Real-Time Physical Braille Recognition Platform

## Mission

Bridge the last-mile accessibility gap between physical Braille and digital understanding, for every user, in every language, on every device.

---

## Core Goals

1. **Real-time recognition** of physical, embossed Braille via camera (web/mobile/desktop)
2. **Multilingual output** — translate recognized Braille to any major world language
3. **Live AI assistant** — a conversational AI embedded in the app for context, clarification, and guidance
4. **Cross-platform** — single PWA codebase covering web, mobile, desktop (+ AR overlay as stretch goal)
5. **Hackathon-ready** — complete, reproducible, judge-verifiable submission

---

## Feature Scope

### MVP (Must Ship)

| Feature                | Description                                             |
| ---------------------- | ------------------------------------------------------- |
| Camera Braille scan    | Live webcam/phone-camera feed → real-time dot detection |
| Dot detection pipeline | YOLOv8n + OpenCV preprocessing hybrid                   |
| Braille-to-English     | Cell classification → Grade 1 English text              |
| Text-to-Speech         | Browser Web Speech API + backend fallback               |
| PWA shell              | Installable on mobile & desktop, offline-capable        |
| Live AI assistant      | Claude API embedded chat for user help                  |
| Result display         | Scrolling translated text panel                         |

### V1.1 (Stretch / Judges' Bonus)

| Feature             | Description                                                   | Status |
| ------------------- | ------------------------------------------------------------- | ------ |
| Multilingual output | Translate result to any language via LibreTranslate or Claude | Built  |
| Cardboard VR mode   | SBS split-screen phone-in-headset with camera passthrough and 3D floating text | **Shipped** |
| Smart Glasses / WebXR | Three.js spatial text billboards for Meta Quest, Apple Vision Pro | **Shipped** |
| Hands-free mode     | Voice commands + audio beep guidance + verbal alignment prompts | **Shipped** |
| History & export    | Save past scans, export as PDF/TXT                            | Built  |
| Confidence heatmap  | Visual highlight of low-confidence cells                      | Planned |
| Batch image upload  | Process a photo or PDF of a Braille page                      | Built  |

### Out of Scope (This Hackathon)

- Grade 2 contracted Braille (dictionary-compressed — post-hackathon)
- Braille music notation
- Braille math notation (Nemeth code)
- Hardware-specific integrations (refreshable Braille displays)

---

## User Personas

### Persona 1 — Rohan, 28 — Blind Graduate Student (Mumbai)

- **Goal**: Read Braille handouts from professors without waiting for a sighted helper
- **Pain**: Current apps only handle digital Braille; none work on paper
- **Delight**: Speaks result aloud automatically in his language (Hindi/English)

### Persona 2 — Priya, 42 — Parent of a Blind Child (Pune)

- **Goal**: Verify her child's Braille homework is correct
- **Pain**: She can't read Braille; tutors are expensive and rare
- **Delight**: Points phone at notebook, hears what the child wrote

### Persona 3 — Dr. Arvind, 55 — Accessibility NGO Director (Delhi)

- **Goal**: Train volunteers to work with Braille materials at scale
- **Pain**: Volunteers spend 80% of meeting time decoding instead of discussing
- **Delight**: App handles decoding; volunteers focus on meaning and discussion

### Persona 4 — Nour, 22 — Sighted Friend/Caregiver (Dubai)

- **Goal**: Help her blind friend read a Braille menu at a restaurant
- **Pain**: No app handles real physical Braille well; Google Lens fails
- **Delight**: AR overlay shows English text floating above Braille dots in real time

### Persona 5 — Amira, 31 — Blind Power User with a Meta Quest (Cairo)

- **Goal**: Read Braille textbooks completely hands-free while seated
- **Pain**: Phone-based apps require her to hold and tap — impossible during long reading sessions
- **Delight**: Places Braille book on desk, phone scans it, and translated text floats as 3D billboards inside her Quest headset — purely voice-controlled, zero touch needed

---

## Unique Value Proposition

> "Point any camera at physical Braille — get spoken text in your language, instantly."

---

## Success Metrics (Hackathon)

- ≥ 85% character-level accuracy on clean embossed Braille under standard lighting
- ≥ 70% accuracy on real-world noisy/angled images
- < 2 seconds latency from frame capture to speech output
- Demo works live in front of judges with a real Braille book
- All submission requirements met (GitHub, model weights, dataset, training code)
