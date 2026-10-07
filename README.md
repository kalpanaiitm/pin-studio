# 📌 Pin Studio

**Turn a blog post or product page into 15 SEO-ready Pinterest pins, with a bulk-upload file and a posting schedule, in about a minute and for about 1–2p.**

Built by Dr Kalpana Govindarasan for [MoneySavvyUK](https://moneysavvyuk.com), a UK personal-finance blog. It runs on your own computer; your OpenAI key never leaves it.

![Example pins](docs/example-pins.png)

## What it does
1. **Reads the page:** title, headings, lists, main image and price (WordPress posts and Payhip products).
2. **Suggests Pinterest keywords:** one main keyword plus 8–12 related ones, for you to edit.
3. **Writes 15 pins**, each with a different angle and layout (guide, checklist, mistakes, steps, statement, flow, product photo), following Pinterest SEO rules:
   - keyword in the first 40 characters of the title, max 100 characters
   - natural 2–3 sentence descriptions, no hashtag stuffing
   - keyword text on the image, keyword file names, alt text, a board for each pin
4. **Checks every pin** before you publish:
   - **Fact guard:** flags any number, £ amount or percentage that isn't in your post. Personal-finance content must not invent figures.
   - title and description lengths, keyword placement, duplicate titles across all past batches, board names, design limits
5. **Designs the pins** at 1000 × 1500 in your brand colours (Pillow, no AI image costs).
6. **Schedules and exports:** 10 pins a day between 08:00 and 21:00 UK time, at most 3 per post per day, mixed with earlier batches, within Pinterest's 14-day window. You get a zip with the PNGs, a **Pinterest bulk-upload CSV** (image links point to your WordPress uploads folder) and a copy file.

## Quick start (Windows)
```powershell
git clone https://github.com/kalpanaiitm/pin-studio.git
cd pin-studio
.\setup_windows.ps1          # creates .venv, installs, creates .env
notepad .env                 # paste your OpenAI key after OPENAI_API_KEY=
streamlit run app.py         # or double-click start.bat
```
No key yet? Set `LLM_MODE=mock` in `.env` for a free offline mode, which writes plainer copy from the post's own headings.

Command line: `python cli.py https://moneysavvyuk.com/your-post/ --month 2026/10`

## Publishing a batch
1. **WordPress → Media → Add New:** upload all PNGs from the zip **without renaming them**.
2. Open one image link to check it works.
3. **Pinterest bulk upload:** upload `pinterest_bulk_upload.csv`, ideally the same day (publish dates must be in the future and within about 14 days).
   No bulk option on your account? Use `PIN_COPY.txt` with Pinterest's normal multi-image upload instead.

## Settings (`settings.yaml`)
- `boards`: **must match your Pinterest board names exactly**
- `brand`: colours, site name, button text
- `schedule`: pins per day, hours, max per post per day, 14-day horizon
- `pinterest_csv`: column names and date format (change these if Pinterest's template differs)
- `llm`: model and prices for the cost meter (default `gpt-4o-mini`)

## Cost
Two API calls per post (keywords, then pins): roughly 6–8k input and 3–4k output tokens. With gpt-4o-mini, that's well under 1p per post. The app shows the running cost.

## How it's built
`pinstudio/fetch.py` (page reader) · `prompts.py` (Pinterest SEO and accuracy rules) · `llm.py` (OpenAI over HTTPS, JSON mode, retries, cost meter) · `mock.py` (offline generator) · `validate.py` (checks and fact guard) · `render.py` (7 layouts) · `schedule.py` · `export.py` · `app.py` (Streamlit) · `cli.py`

**Tests:** `python -m pytest -q` (21 tests, including an end-to-end run against a simulated OpenAI reply, the fact guard, scheduling across BST and the CSV format).

## Licence
Code: MIT. Fonts: Inter, SIL Open Font Licence (`assets/fonts/LICENSE-Inter.txt`).
