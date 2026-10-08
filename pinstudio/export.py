"""Write images, the Pinterest bulk-upload CSV, a copy file and the history log; zip it all."""
import csv
import zipfile
from datetime import datetime
from pathlib import Path

HISTORY_FIELDS = ["created", "batch", "link", "title", "filename", "board", "publish_local", "publish_utc", "image_hash"]


def image_hash(img) -> str:
    """Fingerprint of the finished pin image (same picture = same hash, whatever the file name)."""
    import hashlib
    return hashlib.sha256(img.convert("RGB").resize((200, 300)).tobytes()).hexdigest()[:16]


def media_url(settings, filename: str, upload_month: str) -> str:
    wp = settings["wordpress"]
    return f"{wp['base_url'].rstrip('/')}{wp['uploads_path']}/{upload_month}/{filename}.png"


def read_history(path: Path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def append_history(path: Path, rows):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HISTORY_FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in HISTORY_FIELDS})


def pinterest_rows(pins, settings, upload_month):
    cols = settings["pinterest_csv"]["columns"]
    rows = []
    for p in pins:
        values = {"Title": p["title"], "Media URL": media_url(settings, p["filename"], upload_month),
                  "Pinterest board": p["board"], "Thumbnail": "", "Description": p["description"], "Link": p["link"],
                  "Publish date": p.get("publish_utc", ""), "Keywords": ", ".join(p.get("keywords", []))}
        rows.append({c: values.get(c, "") for c in cols})
    return rows


def export_batch(pins, images, settings, out_root: Path, history_path: Path, upload_month: str, batch_name: str):
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    folder = Path(out_root) / f"{stamp}-{batch_name}"[:80]
    folder.mkdir(parents=True, exist_ok=True)
    for p, img in zip(pins, images):
        img.save(folder / f"{p['filename']}.png", optimize=True)
    rows = pinterest_rows(pins, settings, upload_month)
    max_rows = settings["pinterest_csv"]["max_rows"]
    csv_files = []
    for i in range(0, len(rows), max_rows):
        f = folder / f"pinterest_bulk_upload{'' if i == 0 else f'_{i // max_rows + 1}'}.csv"
        with f.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=settings["pinterest_csv"]["columns"])
            w.writeheader()
            w.writerows(rows[i:i + max_rows])
        csv_files.append(f)
    with (folder / "PIN_COPY.txt").open("w", encoding="utf-8") as fh:
        fh.write(f"Pins for {batch_name}\nUpload the PNG images to WordPress in {upload_month} before uploading the CSV to Pinterest.\n\n")
        for p in pins:
            fh.write(f"=== {p['filename']}.png ===\nPUBLISH (UK time): {p.get('publish_local', 'not scheduled')}\n"
                     f"BOARD: {p['board']}\nTITLE: {p['title']}\nDESCRIPTION: {p['description']}\nALT TEXT: {p['alt']}\n"
                     f"KEYWORDS: {', '.join(p.get('keywords', []))}\nLINK: {p['link']}\n\n")
    zip_path = folder.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(folder.iterdir()):
            z.write(f, f"{folder.name}/{f.name}")
    append_history(history_path, [{**p, "created": stamp, "batch": batch_name, "image_hash": image_hash(img)}
                                  for p, img in zip(pins, images)])
    return folder, zip_path, csv_files
