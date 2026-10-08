"""Pin Studio: run with  streamlit run app.py"""
import hashlib
import io
import json
from datetime import date, datetime

import streamlit as st

from pinstudio.batch import build_for_url, capacity, schedule_and_export
from pinstudio.config import load_settings, paths, save_prefs
from pinstudio.export import export_batch, read_history
from pinstudio.fetch import fetch_page
from pinstudio.generate import make_pins, recheck, regenerate_one, suggest_keywords
from pinstudio.llm import LLM
from pinstudio.prompts import LAYOUTS
from pinstudio.render import load_image, render_pin
from pinstudio.schedule import plan

st.set_page_config(page_title="Pin Studio · MoneySavvyUK", page_icon="📌", layout="wide")
S = load_settings()
P = paths()
ss = st.session_state
ss.setdefault("llm", LLM(S))
llm = ss.llm
history = read_history(P["history"])

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("📌 Pin Studio")
    st.caption(f"Brand: **{S['brand']['name']}**")
    if llm.mode == "mock":
        st.info("Offline mode: free and instant, but plainer copy. Set LLM_MODE or settings.yaml to use OpenAI.")
    elif llm.ready:
        st.success(f"OpenAI connected · {S['llm']['model']}")
    else:
        st.error("No OpenAI key found. Copy .env.example to .env and paste your key, then restart.")
    st.metric("AI cost this session", f"${llm.cost_usd:.4f}", help=f"{llm.calls} calls · {llm.tokens_in + llm.tokens_out:,} tokens")
    upcoming = [h for h in history if h.get("publish_local") and h["publish_local"][:10] >= date.today().isoformat()]
    st.metric("Pins already scheduled", len(upcoming))
    if upcoming:
        st.caption(f"Last scheduled: {max(h['publish_local'] for h in upcoming)[:16].replace('T', ' ')}")
    st.divider()
    ppd = st.number_input("Pins per day", min_value=5, max_value=25, value=int(S["schedule"]["pins_per_day"]), step=1,
                          help="Spread between your posting hours, max 3 per post per day.")
    if ppd != S["schedule"]["pins_per_day"]:
        save_prefs(pins_per_day=int(ppd))
        S["schedule"]["pins_per_day"] = int(ppd)
    st.caption(f"Pinterest schedules up to {S['schedule']['horizon_days']} days ahead, so up to **{capacity(S)} pins** at a time. "
               f"Reaching {ppd} a day needs pins from at least {-(-ppd // S['schedule']['max_per_link_per_day'])} different posts.")
    mode = st.radio("Mode", ["One post (review each pin)", "Several posts at once"], key="mode")
    st.divider()
    st.caption("Boards, colours and posting hours are in **settings.yaml**.")
    if st.button("Start a new post"):
        for k in ("page", "kw", "pins", "export"):
            ss.pop(k, None)
        st.rerun()


def show_error(error):
    st.error(f"{error}")


def show_export(exp, month):
    if exp["done"]:
        st.success(f"{len(exp['done'])} pins scheduled from {exp['done'][0]['publish_local'][:10]} to {exp['done'][-1]['publish_local'][:10]}.")
    else:
        st.error(f"Nothing could be scheduled in the next {S['schedule']['horizon_days']} days: the schedule is already full.")
    if exp.get("blocked_duplicates"):
        st.warning(f"Left out {len(exp['blocked_duplicates'])} pin(s) whose image was already scheduled before: "
                   + "; ".join(exp["blocked_duplicates"][:5]))
    if exp["left"]:
        st.warning(f"{exp['left']} pin(s) didn't fit in Pinterest's {S['schedule']['horizon_days']}-day window. Make them in a later batch.")
    if not exp["done"]:
        return
    with open(exp["zip"], "rb") as fh:
        st.download_button("⬇️ Download pins + Pinterest CSV (zip)", fh, file_name=exp["zip"].replace("\\", "/").split("/")[-1])
    st.dataframe([{"When (UK)": p["publish_local"][:16].replace("T", " "), "Title": p["title"], "Board": p["board"]}
                  for p in exp["done"]], use_container_width=True, hide_index=True)
    first = exp["done"][0]["filename"]
    st.markdown(f"""**Next steps**
1. In WordPress go to **Media → Add New** and upload all the PNG files from the zip. **Don't rename them.**
2. Open one image link to check it works, e.g. `{S['wordpress']['base_url']}{S['wordpress']['uploads_path']}/{month}/{first}.png`
3. On Pinterest go to **Settings → Create Pins in bulk** and upload **pinterest_bulk_upload.csv** the **same day** (dates must be in the future).
4. Check **Scheduled Pins** on your profile after a couple of hours. Files are also saved in `{exp['folder']}`.""")


# ================================================================ bulk mode
if mode == "Several posts at once":
    st.title("Pins for several posts at once")
    st.caption("Paste blog post or Payhip links, one per line. Each gets keywords and pins automatically (no review step), "
               "then everything is scheduled together and mixed so no post dominates a day.")
    urls_text = st.text_area("Links", height=180, placeholder="https://moneysavvyuk.com/how-to-sell-on-vinted-uk/\nhttps://payhip.com/b/l09hx")
    urls = list(dict.fromkeys(u.strip() for u in urls_text.splitlines() if u.strip().startswith("http")))
    per_post = st.slider("Pins per post", 5, 20, int(S["pins_per_post"]))
    total = len(urls) * per_post
    if urls:
        st.caption(f"{len(urls)} link(s) × {per_post} = **{total} pins** ≈ {total / S['schedule']['pins_per_day']:.1f} days at "
                   f"{S['schedule']['pins_per_day']} a day · estimated AI cost about ${0.0015 * len(urls):.3f}")
        if total > capacity(S):
            st.warning(f"That's more than fits in {S['schedule']['horizon_days']} days ({capacity(S)} pins). Extra pins will be left for a later batch.")
    if st.button("Make pins for all", type="primary", disabled=not (urls and llm.ready)):
        results, all_pins = [], []
        progress = st.progress(0.0)
        titles = [h["title"] for h in history]
        for i, url in enumerate(urls, 1):
            try:
                page, kw, pins = build_for_url(url, S, llm, titles + [p["title"] for p in all_pins], per_post)
                errs = sum(1 for p in pins for x in p["issues"] if x["level"] == "error")
                results.append({"Post": page.title[:70], "Keyword": kw["main_keyword"], "Pins": len(pins), "To check": errs, "Status": "ok"})
                all_pins += [{**p, "_url_issues": errs} for p in pins]
            except Exception as e:
                results.append({"Post": url, "Keyword": "", "Pins": 0, "To check": 0, "Status": f"failed: {e}"})
            progress.progress(i / len(urls))
        ss.bulk = {"results": results, "pins": all_pins}
        ss.pop("bulk_export", None)
    bulk = ss.get("bulk")
    if bulk:
        st.dataframe(bulk["results"], use_container_width=True, hide_index=True)
        flagged = [p for p in bulk["pins"] if any(x["level"] == "error" for x in p["issues"])]
        if flagged:
            with st.expander(f"🔴 {len(flagged)} pin(s) flagged; they will be left out unless you include them"):
                for p in flagged:
                    st.write(f"**{p['title']}**: " + "; ".join(x["msg"] for x in p["issues"] if x["level"] == "error"))
        include_flagged = st.checkbox("Include flagged pins anyway", value=False) if flagged else False
        chosen = [p for p in bulk["pins"] if include_flagged or p not in flagged]
        month_b = st.text_input("WordPress upload month", date.today().strftime("%Y/%m"), key="bulk_month")
        if st.button(f"Schedule & create upload files for {len(chosen)} pins", type="primary", disabled=not chosen):
            with st.spinner("Designing full-size pins and scheduling…"):
                ss.bulk_export = schedule_and_export(chosen, S, P, history, month_b, f"bulk-{len(urls)}-posts")
        if ss.get("bulk_export"):
            show_export(ss.bulk_export, month_b)
    st.stop()

# ---------------------------------------------------------------- step 1: page
st.title("Turn a post into 15 Pinterest pins")
url = st.text_input("1 · Paste a MoneySavvyUK blog post or Payhip product link", value=ss.get("page").url if ss.get("page") else "",
                    placeholder="https://moneysavvyuk.com/how-to-sell-on-vinted-uk/")
if st.button("Read page", type="primary", disabled=not url):
    try:
        with st.spinner("Reading the page…"):
            ss.page = fetch_page(url.strip())
        for k in ("kw", "pins", "export"):
            ss.pop(k, None)
    except Exception as e:
        show_error(e)

page = ss.get("page")
if not page:
    st.stop()
st.success(f"**{page.title}** · {page.kind} · {len(page.sections)} sections" + (f" · {page.price}" if page.price else ""))
with st.expander("What the app read from the page"):
    st.text(page.outline())

# ---------------------------------------------------------------- step 2: keywords
st.subheader("2 · Keywords")
if "kw" not in ss:
    if st.button("Suggest keywords", type="primary", disabled=not llm.ready):
        try:
            with st.spinner("Finding Pinterest keywords…"):
                ss.kw = suggest_keywords(page, S, llm)
            st.rerun()
        except Exception as e:
            show_error(e)
    st.stop()

kw = ss.kw
c1, c2 = st.columns([1, 1])
kw["main_keyword"] = c1.text_input("Main keyword (goes first in titles)", kw["main_keyword"])
board_list = S["boards"]
kw["board_suggestion"] = c1.selectbox("Default board", board_list,
                                      index=board_list.index(kw["board_suggestion"]) if kw.get("board_suggestion") in board_list else 0)
related = c2.text_area("Related keywords (one per line)", "\n".join(kw["related_keywords"]), height=180)
kw["related_keywords"] = [k.strip().lower() for k in related.splitlines() if k.strip()]
if kw.get("notes"):
    st.caption(f"💡 {kw['notes']} Tip: type two or three of these into Pinterest's search bar to check people really search for them.")

# ---------------------------------------------------------------- step 3: pins
st.subheader(f"3 · Create {S['pins_per_post']} pins")
history_titles = [h["title"] for h in history]
if st.button("Create pins" if "pins" not in ss else "Create a fresh set", type="primary", disabled=not llm.ready):
    try:
        with st.spinner("Writing pin ideas and SEO copy…"):
            ss.pins = make_pins(page, kw, S, llm)
            recheck(ss.pins, page, kw, S, history_titles)
            ss.gen = ss.get("gen", 0) + 1
        ss.pop("export", None)
    except Exception as e:
        show_error(e)
if "pins" not in ss:
    st.stop()

pins = ss.pins
photo = load_image(page.image_url) if page.kind == "product" and page.image_url else None


@st.cache_data(show_spinner=False, max_entries=200)
def preview(pin_json: str, cta: str):
    pin = json.loads(pin_json)
    img = render_pin(pin, S["brand"], image=photo if pin["layout"] == "photo" else None, cta=cta)
    buf = io.BytesIO()
    img.resize((400, 600)).save(buf, format="PNG")
    return buf.getvalue()


cta = S["brand"]["cta"] if page.kind == "blog" else S["brand"]["product_cta"]
errors = sum(1 for p in pins for i in p["issues"] if i["level"] == "error")
warns = sum(1 for p in pins for i in p["issues"] if i["level"] == "warn")
st.caption(f"{len(pins)} pins · {errors} to fix · {warns} suggestions. Edit any text below; checks re-run automatically.")

cols = st.columns(3)
for i, pin in enumerate(pins):
    col = cols[i % 3]
    with col:
        design = {k: pin.get(k) for k in ("layout", "kicker", "headline", "sub", "items", "title")}
        st.image(preview(json.dumps(design, sort_keys=True), cta), use_container_width=True)
        badge = "🔴" if any(x["level"] == "error" for x in pin["issues"]) else ("🟡" if pin["issues"] else "🟢")
        with st.expander(f"{badge} {i + 1}. {pin['title'][:60]}"):
            for issue in pin["issues"]:
                (st.error if issue["level"] == "error" else st.warning)(issue["msg"])
            k = f"g{ss.get('gen', 0)}-{pin['filename']}"   # new widgets whenever a pin is replaced or a new set is made
            pin["headline"] = st.text_input("Headline on the pin", pin["headline"], key=f"{k}h")
            pin["kicker"] = st.text_input("Small label", pin["kicker"], key=f"{k}k").upper()
            if pin["layout"] in ("hero", "statement"):
                pin["sub"] = st.text_area("Subtitle", pin.get("sub", ""), key=f"{k}s")
            if pin["layout"] in ("checklist", "mistakes", "steps", "flow"):
                items = st.text_area("Items (one per line)", "\n".join(pin["items"]), key=f"{k}i")
                pin["items"] = [x.strip() for x in items.splitlines() if x.strip()]
            pin["title"] = st.text_input(f"Pin title ({len(pin['title'])}/100)", pin["title"], key=f"{k}t")
            pin["description"] = st.text_area(f"Description ({len(pin['description'])} chars)", pin["description"], key=f"{k}d")
            pin["alt"] = st.text_area("Alt text", pin["alt"], key=f"{k}a")
            pin["board"] = st.selectbox("Board", board_list, index=board_list.index(pin["board"]) if pin["board"] in board_list else 0, key=f"{k}b")
            st.caption(f"File: {pin['filename']}.png · Keywords: {', '.join(pin.get('keywords', []))}")
            lc1, lc2 = st.columns([1, 2])
            new_layout = lc1.selectbox("Layout", [l for l in LAYOUTS if l != "photo" or photo is not None],
                                       index=list(LAYOUTS).index(pin["layout"]) if pin["layout"] in LAYOUTS else 0, key=f"{k}l")
            feedback = lc2.text_input("What should change? (optional)", key=f"{k}f")
            if st.button("🔄 Replace this pin", key=f"{k}r"):
                try:
                    with st.spinner("Writing a new pin…"):
                        ss.pins = regenerate_one(page, kw, S, llm, pins, i, new_layout, feedback)
                    st.rerun()
                except Exception as e:
                    show_error(e)
recheck(pins, page, kw, S, history_titles)

# ---------------------------------------------------------------- step 4: schedule + export
st.subheader("4 · Schedule and export")
today = date.today()
month = st.text_input("WordPress upload month (where you'll upload the images)", today.strftime("%Y/%m"),
                      help="WordPress stores uploads in /wp-content/uploads/YYYY/MM/. Use the month you upload them.")
if errors:
    st.warning(f"{errors} pin(s) have problems marked 🔴. Fix them, or tick below to export anyway.")
force = st.checkbox("Export anyway", value=False) if errors else True
if st.button("Schedule & create upload files", type="primary", disabled=not force):
    with st.spinner("Designing full-size pins and scheduling…"):
        batch = [{**p, "_kind": page.kind, "_image_url": page.image_url if page.kind == "product" else ""} for p in pins]
        name = "-".join(pins[0]["filename"].split("-")[:4]) if pins else "batch"
        ss.export = schedule_and_export(batch, S, P, history, month, name, today=today)

if ss.get("export"):
    show_export(ss.export, month)
