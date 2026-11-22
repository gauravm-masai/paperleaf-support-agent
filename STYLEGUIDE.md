# PaperLeaf Books Support: Style Guide

The look of the Streamlit page (`app.py`), based on your homepage mock-up.
Feel in three words: **calm, editorial, friendly.**

## 1. Colours

| Name | Hex | Used for |
|---|---|---|
| Page | `#F5F3EC` | Page background (warm cream) |
| Card | `#FFFFFF` | Top bar, sidebar, cards, chat box, ticket cards |
| Ink | `#12251C` | Headlines and text |
| Green | `#1B5A45` | Main buttons, customer bubbles, accents, logo tile |
| Green deep | `#144636` | Hover on green buttons |
| Pale green | `#DDEBE1` | Hero panel, Paige's bubbles, avatar circle |
| Tint | `#E8F0EA` | Hover highlights, sample-chat bubble |
| Line | `#D9DFD9` | Hairline borders and dividers |
| Outline | `#33433A` | Thin dark outline on the homepage cards |
| Muted | `#5F6F66` | Captions, timestamps |
| Alert | `#C0392B` | High-priority ticket edge, errors |

Green is the only accent. Do not add a second bright colour.

## 2. Typography

| Use | Font | Weight | Size |
|---|---|---|---|
| Homepage headline | Fraunces (serif) | 500 | 2.8 to 4.7rem, tight (-3.5%), line height 0.98 |
| Page titles and sidebar headings | Fraunces | 600 | 2rem / 1.1rem |
| Body, chat, buttons | Inter | 400 / 600 | 1rem (buttons 1.1 to 1.2rem) |
| Captions | Inter | 400 | 0.85rem, Muted |

## 3. Shape and spacing

- Buttons and cards: rounded rectangles (12 to 14px). Hero panel 28px. Chat bubbles 20px with one squarer corner.
- Chat input: a white pill with a soft shadow.
- One soft shadow only: `0 6px 24px rgba(18,37,28,0.08)`.
- Homepage is centred at 1180px; the chat and admin pages use the full width of the page.

## 4. Homepage

1. **Top bar:** full-width white bar. Logo on the left, "Get support" on the right.
2. **Hero:** left: big serif headline "Get answers from PaperLeaf.", one line of text, and a solid green "Start a conversation" button. Right: a pale green panel with two tilted sheets behind a sample chat (an answer taken from the FAQ).
3. **Three cards** with an icon, a label and an arrow: *Track an order*, *Start a return*, *Delivery costs*. Each opens the passcode box, then asks Paige that question.
4. **Passcode box:** appears under the button when "Start a conversation", "Get support" or a card is clicked. Customer passcode opens a fresh chat; admin passcode opens the admin page.

5. **Info strip:** under the cards, a thin line and three quiet facts with green check marks: free delivery above ₹499, 7-day returns on most items, support 9 AM to 9 PM. They are copied from the FAQ sheet, so update them in `app.py` if the sheet changes.

## 5. Chat page

- **Sidebar (left):** a large logo, the Suggested Questions list, then "Your tickets". "Start a new chat" sits at the very bottom.
- **Title** "PaperLeaf Books Support" at the very top of the page, left-aligned.
- **Width:** the chat uses the whole page width. Bubbles can grow to about 85% of it.
- **Messages:** customer on the right in a green bubble with white text. Paige on the left in a pale green bubble beside a small leaf avatar.
- **Under each reply:** a small "Was this helpful?" with thumbs up and down.
- **While Paige answers:** three softly pulsing green dots in a pale green bubble beside her leaf avatar.
- **Motion (subtle):** new messages fade in over 0.3s; the homepage cards and button lift 2px on hover. Nothing else moves.
- **Admin page:** each saved chat opens as the same bubbles (customer on the right, Paige on the left).
- **Suggested Questions:** a plain left-aligned list of full questions (no borders), with a soft tint on hover.
- **Tickets:** white cards with a green left edge (red for high priority).
- **Chat box:** fixed at the bottom, the same width as the messages.

## 6. Streamlit settings

`.streamlit/config.toml`:
```
[theme]
base = "light"
primaryColor = "#1B5A45"
backgroundColor = "#F5F3EC"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#12251C"
font = "sans serif"
```
All other styling is in the `STYLE` block in `app.py`.

## 7. Dos and don'ts

- Do keep lots of space and one accent colour.
- Do keep wording short and friendly.
- Don't use gradients, glows or neon.
- Don't use emoji as decoration (the leaf picture is the only icon motif).
