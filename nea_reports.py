import os
import glob
import shutil
import math
import mimetypes
import time
import smtplib
import ssl
import imaplib
import email
from email.message import EmailMessage
from datetime import datetime, timedelta
from decimal import Decimal
from dotenv import load_dotenv
import pandas as pd
import xlwings as xw
from pdf2image import convert_from_path
from PIL import Image, ImageFilter
import pytesseract

# ─────────── Configuration ───────────

load_dotenv()
SENDER_EMAIL     = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD  = os.environ["SENDER_PASSWORD"]
# split the comma-separated list into a Python list
RECIPIENT_EMAILS = os.environ["RECIPIENT_EMAILS"].split(",")

# booleans & numbers need casting
POLL_FOR_REPLY    = os.environ.get("POLL_FOR_REPLY", "True").lower() in ("1","true","yes")
POLL_TIMEOUT_MIN  = int(os.environ.get("POLL_TIMEOUT_MIN", "30"))
POLL_INTERVAL_SEC = int(os.environ.get("POLL_INTERVAL_SEC", "10"))

BASE_NEA = os.environ["BASE_NEA"]
BASE_ERC = os.environ["BASE_ERC"]

PDF_PASSWORD    = os.environ["PDF_PASSWORD"]
JPG_DPI         = int(os.environ.get("JPG_DPI", "600"))
TESSERACT_CMD   = os.environ["TESSERACT_CMD"]
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ─────────── Helpers ───────────
def target_date(offset: int = 1) -> datetime:
    """
    Compute the target date corresponding to 'offset' months back.
    offset=1 → last month, offset=2 → two months back, etc.
    """
    d = datetime.today().replace(day=1) - timedelta(days=1)
    for _ in range(offset - 1):
        d = d.replace(day=1) - timedelta(days=1)
    return d

def prev_month(d: datetime) -> datetime:
    """Return the month immediately before the given date 'd'."""
    return d.replace(day=1) - timedelta(days=1)

def month_folder(d: datetime) -> str:
    """Format a folder name as 'MM. MON YYYY' for the given date 'd'."""
    return f"{d.month:02d}. {d.strftime('%b').upper()} {d.year}"

def send_email(subject: str, body: str, paths: list[str]) -> None:
    """
    Send an email with the given subject, body, and list of file paths as attachments.
    """
    msg = EmailMessage()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = ", ".join(RECIPIENT_EMAILS)
    msg["Subject"] = subject
    msg.set_content(body)
    for p in paths:
        mime, _ = mimetypes.guess_type(p)
        maintype, subtype = (mime or "application/octet-stream").split("/", 1)
        with open(p, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(p)
            )
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.send_message(msg)

def send_simple(subject: str, body: str) -> None:
    """
    Send a simple email (no attachments) with given subject and body.
    """
    msg = EmailMessage()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = ", ".join(RECIPIENT_EMAILS)
    msg["Subject"] = subject
    msg.set_content(body)
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.send_message(msg)

def wait_reply(keywords: list[str]) -> str | None:
    """
    Poll the inbox for replies that contain one of the specified keywords 
    (case-insensitive). Return the matching subject/text if found within 
    the timeout, or None if timed out.
    """
    end = time.time() + POLL_TIMEOUT_MIN * 60
    keys = set(k.lower() for k in keywords)
    whitelist = set(e.lower() for e in RECIPIENT_EMAILS)
    while time.time() < end:
        with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
            imap.login(SENDER_EMAIL, SENDER_PASSWORD)
            imap.select("INBOX")
            _, data = imap.search(None, "UNSEEN")
            for num in data[0].split():
                _, md = imap.fetch(num, "(RFC822)")
                m = email.message_from_bytes(md[0][1])
                frm = email.utils.parseaddr(m["From"])[1].lower()
                imap.store(num, "+FLAGS", "\\Seen")
                if frm not in whitelist:
                    continue
                txt = m.get("Subject", "")
                if m.is_multipart():
                    for part in m.walk():
                        if part.get_content_type() == "text/plain":
                            txt += " " + part.get_payload(decode=True).decode(errors="ignore")
                else:
                    txt += " " + m.get_payload(decode=True).decode(errors="ignore")
                words = set(w.strip(".,!?;:()[]\"'") for w in txt.lower().split())
                if words & keys:
                    imap.logout()
                    return txt.lower()
            imap.logout()
        time.sleep(POLL_INTERVAL_SEC)
    return None

# ─────────── Report Steps (Task Functions) ───────────

def process_pdc(offset: int = 1) -> list[str]:
    """
    Generate PDC/PGC/PSR workbooks for 'offset' months back.
    Returns a list of filepaths created or updated.
    """
    d = target_date(offset)
    pm = prev_month(d)
    stamp_cur  = f"{d.year}{d.month:02d}01-V1.xls"
    stamp_prev = f"{pm.year}{pm.month:02d}01-V1.xls"

    codes = [("PDC","PDC"), ("PGC","PGC"), ("PSR","Power Supplier Report")]
    out = []
    for code, sheet in codes:
        base_cur  = os.path.join(BASE_NEA, str(d.year), month_folder(d))
        base_prev = os.path.join(BASE_NEA, str(pm.year), month_folder(pm))

        if code in ("PDC","PGC"):
            name_cur  = f"Compliance to {code}-{stamp_cur}"
            name_prev = f"Compliance to {code}-{stamp_prev}"
        else:
            name_cur  = f"Power Supplier Report-{stamp_cur}"
            name_prev = f"Power Supplier Report-{stamp_prev}"

        path_prev = os.path.join(base_prev, name_prev)
        path_cur  = os.path.join(base_cur, name_cur)

        os.makedirs(os.path.dirname(path_cur), exist_ok=True)
        if os.path.exists(path_prev):
            shutil.copy2(path_prev, path_cur)
        else:
            app = xw.App(visible=False)
            wb  = app.books.add()
            wb.sheets[0].name = sheet
            wb.save(path_cur)
            wb.close()
            app.quit()

        app = xw.App(visible=False)
        wb  = app.books.open(path_cur)
        sh  = wb.sheets[sheet]
        sh.range("C3").value = d.strftime("%B")
        sh.range("C4").value = d.year
        wb.save()
        wb.close()
        app.quit()

        out.append(path_cur)

    return out

def process_interruption(offset: int = 1) -> list[str]:
    """
    Generate Energy and Interruption Data workbook for 'offset' months back.
    Returns a list containing the file path, or an empty list if missing ERC files.
    """
    d = target_date(offset)
    pm = prev_month(d)
    stamp_cur  = f"{d.year}{d.month:02d}01-V1.xls"
    stamp_prev = f"{pm.year}{pm.month:02d}01-V1.xls"
    name_cur  = f"Energy and Interruption Data-{stamp_cur}"
    name_prev = f"Energy and Interruption Data-{stamp_prev}"

    base_cur  = os.path.join(BASE_NEA, str(d.year), month_folder(d))
    base_prev = os.path.join(BASE_NEA, str(pm.year), month_folder(pm))

    path_prev = os.path.join(base_prev, name_prev)
    path_cur  = os.path.join(base_cur, name_cur)

    os.makedirs(os.path.dirname(path_cur), exist_ok=True)
    if os.path.exists(path_prev):
        shutil.copy2(path_prev, path_cur)
    else:
        app = xw.App(visible=False)
        wb  = app.books.add()
        wb.sheets[0].name = "interruption"
        wb.sheets.add("Energy Input and Output", after=wb.sheets[0])
        wb.save(path_cur)
        wb.close()
        app.quit()

    plan_pat   = os.path.join(BASE_ERC, f"{d.year} POWER INTERRUPTIONS",
                              f"*{d.month:02d}_{d.strftime('%B').upper()}*PLANNED*.xlsx")
    unplan_pat = os.path.join(BASE_ERC, f"{d.year} POWER INTERRUPTIONS",
                              f"*{d.month:02d}_{d.strftime('%B').upper()}*UNPLANNED*.xlsx")
    planned   = next(iter(glob.glob(plan_pat)), None)
    unplanned = next(iter(glob.glob(unplan_pat)), None)
    if not planned or not unplanned:
        return []

    df1 = pd.read_excel(planned, skiprows=11)
    df2 = pd.read_excel(unplanned, skiprows=11)
    df  = pd.concat([df1, df2])
    df  = df[~df.iloc[:,0].astype(str).str.contains("Totals", na=False)].dropna()
    df.iloc[:,0] = pd.to_datetime(df.iloc[:,0], format="%m/%d/%y", errors="coerce")
    df = df.sort_values(df.columns[0]).reset_index(drop=True)

    app = xw.App(visible=False)
    wb  = app.books.open(path_cur)
    out = wb.sheets["Energy Input and Output"]
    out.range("C3").value = d.strftime("%B")
    out.range("C4").value = d.year
    sh = wb.sheets["interruption"]
    sh.range("B19:G1000").clear_contents()
    sh.range("I19:M1000").clear_contents()
    start_row, start_col = 19, 2
    protected = {8, 16}
    for i, row in enumerate(df.itertuples(index=False)):
        for j, val in enumerate(row):
            col = start_col + j
            while col in protected:
                col += 1
            sh.range((start_row + i, col)).value = val
    wb.save()
    wb.close()
    app.quit()

    return [path_cur]

def process_supply(offset: int = 1) -> list[str]:
    """
    Generate Power Supply workbook (OCR-based) for 'offset' months back.
    Returns a list containing the file path.
    """
    MONTH_TO_COL = {1:"C",2:"D",3:"E",4:"F",5:"G",6:"H",7:"I",8:"J",9:"K",10:"L",11:"M",12:"N"}

    d = target_date(offset)
    pm = prev_month(d)
    stamp_cur  = f"{d.year}{d.month:02d}01-V1.xls"
    stamp_prev = f"{pm.year}{pm.month:02d}01-V1.xls"

    base_sup   = os.path.join(BASE_NEA, str(d.year), month_folder(d), "SUPPORTING DOCS")
    pdf17      = os.path.join(base_sup, "17MW.pdf")
    pdfEx      = os.path.join(base_sup, "Excess.pdf")

    base_cur   = os.path.join(BASE_NEA, str(d.year), month_folder(d))
    base_prev  = os.path.join(BASE_NEA, str(pm.year), month_folder(pm))

    name_cur   = f"Power Supply-{stamp_cur}"
    name_prev  = f"Power Supply-{stamp_prev}"
    path_prev  = os.path.join(base_prev, name_prev)
    path_cur   = os.path.join(base_cur, name_cur)

    os.makedirs(os.path.dirname(path_cur), exist_ok=True)
    if os.path.exists(path_prev):
        shutil.copy2(path_prev, path_cur)
    else:
        app = xw.App(visible=False)
        w   = app.books.add()
        w.sheets[0].name = "Power Supply"
        w.save(path_cur)
        w.close()
        app.quit()

    pages17 = convert_from_path(pdf17, dpi=JPG_DPI, first_page=2, last_page=2, userpw=PDF_PASSWORD)
    pagesEx = convert_from_path(pdfEx, dpi=JPG_DPI, first_page=2, last_page=2, userpw=PDF_PASSWORD)
    img17, imgEx = pages17[0], pagesEx[0]

    BOX_SI  = (3720, 1335, 4550, 1440)
    BOX_SD  = (1110, 2484, 1772, 2580)
    BOX_ED  = (320, 2576, 1000, 2680)
    BOX_SUM = (4193, 3837, 4783, 4033)
    BOX_TX  = (4260, 4176, 4781, 4259)

    def ocr_img(pil_img: Image.Image, box: tuple[int,int,int,int], psm: str = "7") -> str:
        crop = pil_img.crop(box)
        bw   = crop.convert("L").filter(ImageFilter.MedianFilter(3)).point(lambda x: 0 if x < 140 else 255)
        return pytesseract.image_to_string(bw, config=f"--psm {psm}").strip()

    def ocr_sum_img(pil_img: Image.Image, box: tuple[int,int,int,int]) -> Decimal:
        raw = ocr_img(pil_img, box, "6 -c tessedit_char_whitelist=0123456789.,")
        return sum(Decimal(x.replace(",", "")) for x in raw.splitlines() if x.strip())

    si = f"{ocr_img(img17, BOX_SI)} & {ocr_img(imgEx, BOX_SI)}"
    sd = ocr_img(img17, BOX_SD)
    ed = ocr_img(img17, BOX_ED)
    gt = ocr_sum_img(img17, BOX_SUM) + ocr_sum_img(imgEx, BOX_SUM)
    tx = ocr_sum_img(img17, BOX_TX)  + ocr_sum_img(imgEx, BOX_TX)

    fsc = os.path.join(base_sup, f"Fscsrd{d.year}.xlsx")
    csrd_l = 0
    csrd_k = 0
    if os.path.exists(fsc):
        try:
            col = MONTH_TO_COL[d.month]
            app_xw = xw.App(visible=False)
            wb_xw = app_xw.books.open(fsc)
            sh_xw = wb_xw.sheets["CSRDDetails"]
            csrd_l = sh_xw.range(f"{col}105").value or 0
            csrd_k = sh_xw.range(f"{col}192").value or 0
            wb_xw.close()
            app_xw.quit()
        except Exception:
            csrd_l = 0
            csrd_k = 0

    app = xw.App(visible=False)
    w   = app.books.open(path_cur)
    sh  = w.sheets["Power Supply"]
    sh.range("C3").value = d.strftime("%B")
    sh.range("C4").value = d.year
    sh.range("D12").value = si
    sh.range("E12").value = sd
    sh.range("F12").value = ed
    sh.range("H12").value = str(gt)
    sh.range("I12").value = str(tx)
    sh.range("K12").value = str(csrd_k)
    sh.range("L12").value = str(csrd_l)
    w.save()
    w.close()
    app.quit()

    return [path_cur]

def process_ngcp(offset: int = 1) -> list[str]:
    """
    Generate NGCP Bill workbook (OCR-based) for 'offset' months back.
    Returns a list containing the file path, or an empty list on failure.
    """
    d  = target_date(offset)
    pm = prev_month(d)
    stamp_cur  = f"{d.year}{d.month:02d}01-V1.xls"
    stamp_prev = f"{pm.year}{pm.month:02d}01-V1.xls"

    base_sup   = os.path.join(BASE_NEA, str(d.year), month_folder(d), "SUPPORTING DOCS")
    pdf_path   = os.path.join(base_sup, "NGCP BILL.pdf")
    base_cur   = os.path.join(BASE_NEA, str(d.year), month_folder(d))
    base_prev  = os.path.join(BASE_NEA, str(pm.year), month_folder(pm))

    name_cur   = f"NGCP Bill-{stamp_cur}"
    name_prev  = f"NGCP Bill-{stamp_prev}"
    path_prev  = os.path.join(base_prev, name_prev)
    path_cur   = os.path.join(base_cur, name_cur)

    os.makedirs(os.path.dirname(path_cur), exist_ok=True)
    if os.path.exists(path_prev):
        shutil.copy2(path_prev, path_cur)
    else:
        app = xw.App(visible=False)
        w   = app.books.add()
        w.sheets[0].name = "NGCP Bill"
        w.save(path_cur)
        w.close()
        app.quit()

    try:
        pages = convert_from_path(pdf_path, dpi=JPG_DPI, userpw=PDF_PASSWORD)
    except Exception:
        return []

    FIELD_MAP = {
        "C11": (0, (4330,  477, 4730,  542)),  # statement date (page 1)
        "C12": (0, (4060,  600, 4725,  681)),  # power bill ref (page 1)
        "C15": (1, (4471, 2641, 4706, 2724)),  # BDD           (page 2)
        "C16": (1, (4391, 2774, 4705, 2851)),  # BDE           (page 2)
        "C17": (1, (4389, 2899, 4706, 2973)),  # RRE           (page 2)
        "C18": (1, (4488, 3030, 4707, 3102)),  # power factor  (page 2)
        "C19": (1, (4485, 3150, 4701, 3230)),  # load factor   (page 2)
        "C21": (1, (4615, 3283, 4702, 3361)),  # meter points  (page 2)
        "C24": (2, (3400, 4920, 3778, 4985)),  # total charges (page 3)
        "C25": (2, (3877, 4925, 4220, 4986)),  # total taxes   (page 3)
    }

    def ocr_val(img: Image.Image, box: tuple[int,int,int,int], page_idx: int, total_pages: int) -> str:
        if page_idx >= total_pages:
            return "[PAGE MISSING]"
        crop = img.crop(box)
        bw   = (crop.convert("L")
                      .filter(ImageFilter.MedianFilter(3))
                      .point(lambda x: 0 if x < 140 else 255))
        return pytesseract.image_to_string(bw, config="--psm 7").strip()

    total_pages = len(pages)
    results = {}
    for cell, (page_idx, box) in FIELD_MAP.items():
        val = ocr_val(pages[page_idx if page_idx < total_pages else 0], box, page_idx, total_pages)
        results[cell] = val

    app = xw.App(visible=False)
    w   = app.books.open(path_cur)
    sh  = w.sheets["NGCP Bill"]
    sh.range("C3").value = d.strftime("%B")
    sh.range("C4").value = d.year
    for cell, val in results.items():
        sh.range(cell).value = val
    w.save()
    w.close()
    app.quit()

    return [path_cur]

def process_distribution(offset: int = 1) -> list[str]:
    """
    Generate Distribution Lines Substation & Power Quality workbook for 'offset' months back.
    Returns a list containing the file path.
    """
    d  = target_date(offset)
    pm = prev_month(d)
    stamp_cur  = f"{d.year}{d.month:02d}01-V1.xls"
    stamp_prev = f"{pm.year}{pm.month:02d}01-V1.xls"

    base_sup   = os.path.join(BASE_NEA, str(d.year), month_folder(d), "SUPPORTING DOCS")
    base_cur   = os.path.join(BASE_NEA, str(d.year), month_folder(d))
    base_prev  = os.path.join(BASE_NEA, str(pm.year), month_folder(pm))

    name_cur   = f"Distribution Lines Substation & Power Quality-{stamp_cur}"
    name_prev  = f"Distribution Lines Substation & Power Quality-{stamp_prev}"
    path_prev  = os.path.join(base_prev, name_prev)
    path_cur   = os.path.join(base_cur, name_cur)
    comp       = os.path.join(base_sup, f"COMPLETE DATA {d.year}.xlsx")

    os.makedirs(os.path.dirname(path_cur), exist_ok=True)
    if os.path.exists(path_prev):
        shutil.copy2(path_prev, path_cur)
    else:
        app = xw.App(visible=False)
        w   = app.books.add()
        w.sheets[0].name = "DistLines,Subs,and PowerQuality"
        w.save(path_cur)
        w.close()
        app.quit()

    app = xw.App(visible=False)
    wb  = app.books.open(comp)
    sh  = wb.sheets["DATA"]
    row = 3 + d.month
    areas = [
        ("Toledo",      "BI", "BJ", 70),
        ("Balamban",    "DA", "DB", 71),
        ("Lutupan",     "BI", "BJ", 72),
        ("Asturias",    "DQ", "DR", 73),
        ("Pinamungajan","FD", "FE", 74)
    ]
    data = {}
    for nm, pc, oc, _ in areas:
        pk = sh.range(f"{pc}{row}").value or 0
        op = sh.range(f"{oc}{row}").value or 0
        s3 = math.sqrt(3)
        if nm in ("Toledo","Lutupan","Pinamungajan"):
            pc_v = (pk * s3) / 1000
            oc_v = (op * s3) / 1000
            sp_v = pc_v / (33500 / 13200)
            so_v = oc_v / (33500 / 13200)
        else:
            sp_v = (pk * s3) / 1000
            so_v = (op * s3) / 1000
            pc_v = sp_v * (67000 / 13200)
            oc_v = so_v * (67000 / 13200)
        data[nm] = (pc_v, oc_v, sp_v, so_v)
    wb.close()
    app.quit()

    app = xw.App(visible=False)
    wb  = app.books.open(path_cur)
    sh  = wb.sheets["DistLines,Subs,and PowerQuality"]
    sh.range("C3").value = d.strftime("%B")
    sh.range("C4").value = d.year
    for nm, _, _, rw in areas:
        pc_v, oc_v, sp_v, so_v = data[nm]
        sh.range(f"D{rw}").value = pc_v
        sh.range(f"E{rw}").value = oc_v
        sh.range(f"F{rw}").value = sp_v
        sh.range(f"G{rw}").value = so_v
    wb.save()
    wb.close()
    app.quit()

    return [path_cur]

# ─────────── Combined Runner Function ───────────

def run_all(offset: int = 1) -> list[str]:
    """
    Run all five reports in sequence using the given offset.
    Returns a combined list of all generated file paths.
    """
    steps = [
        ("PDC/PGC/PSR",   process_pdc),
        ("Interruption",  process_interruption),
        ("Supply OCR",    process_supply),
        ("NGCP OCR",      process_ngcp),
        ("Distribution",  process_distribution),
    ]

    all_paths: list[str] = []
    for name, fn in steps:
        try:
            pts = fn(offset)
            if pts:
                all_paths.extend(pts)
        except Exception as e:
            # Let the caller catch or log this exception as needed
            raise RuntimeError(f"Error in step '{name}': {e}") from e

    # If no files were produced, return empty list
    return all_paths

# Note: The main() function and argparse block have been removed.
# To invoke manually (outside of a web UI), you might do:
# >>> from nea_reports import run_all
# >>> generated_files = run_all(offset=1)
# >>> if generated_files:
# >>>     # e.g. send email or log success
# >>> else:
# >>>     # no files generated
