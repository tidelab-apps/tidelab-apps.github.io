"""Builds the static Tidelab site (GitHub Pages, branch main, root folder).

    python -I -X utf8 build.py            # writes the pages, warns about missing values in config.json
    python -I -X utf8 build.py --release  # the same, but fails while a {{PLACEHOLDER}} is left in any page

The Decklet privacy, support and terms texts come from the Decklet repository (DECKLET_LEGAL below, or --decklet-legal <file>),
so they are written in one place only. The pages use no scripts, no cookies, no analytics and nothing from other sites.
"""
import argparse
import html
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
DECKLET_LEGAL = HERE.parents[1] / "ios-apps" / "srs-cards" / "Design" / "appstore" / "legal" / "build.py"
YEAR = "2026"
APP_STORE_URL = "https://apps.apple.com/app/id6829718725"
BACKUP_UPDATED = "2026-11-01"
EULA = "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/"
KINDS = ("privacy", "support", "terms")
LANGS = ("en", "ru", "de")
# English only for now (owner, 2026-11-01): the ru and de Decklet pages are still built and served at their
# addresses, but no page links to them and there is no language switch. To bring the switch back, pass
# {code: href} as langs to shell() again.

# ---------------------------------------------------------------- texts that only the site has

UI = {
    "en": {"soon": "Available on the App Store", "about": "About", "contact": "Contact",
           "footer": "This site uses no cookies, no analytics and no content from other sites.",
           "free": "Free to study", "info": "Help and legal", "pro": "Decklet Pro", "home": "Tidelab"},
    "ru": {"soon": "Доступно в App Store", "about": "О приложении", "contact": "Контакт",
           "footer": "Этот сайт не использует cookies, аналитику и материалы с других сайтов.",
           "free": "Бесплатно", "info": "Помощь и документы", "pro": "Decklet Pro", "home": "Tidelab"},
    "de": {"soon": "Im App Store verfügbar", "about": "Über die App", "contact": "Kontakt",
           "footer": "Diese Website nutzt keine Cookies, keine Analyse und keine Inhalte anderer Websites.",
           "free": "Kostenlos", "info": "Hilfe und Rechtliches", "pro": "Decklet Pro", "home": "Tidelab"},
}

DECKLET = {
    "en": {
        "title": "Decklet: private, offline study cards",
        "tagline": "Private, offline study cards",
        "intro": "Decklet is a flashcard app with spaced repetition for iPhone. Your notes stay on your iPhone.",
        "features": [
            ("free", "Study free, without limits", "Spaced repetition (FSRS) shows each card just before you would forget it. Any number of decks and cards, no daily limit, no ads."),
            ("free", "Start in one tap", "Lock Screen and Home Screen widgets and a Control Center button start a session. Daily reminder, streak and statistics."),
            ("pro", "Cards from your own material", "Scan a page, choose photos or PDF files, or paste your notes. AI writes the cards on your iPhone with Apple Intelligence, and you check them before they are saved."),
            ("free", "Bring your decks", "Import from other flashcard apps (.apkg), pasted text and CSV. Back up to a file and export any deck as CSV."),
        ],
        "pills": ["No account", "No tracking", "No analytics", "Works offline"],
    },
    "ru": {
        "title": "Decklet: карточки для запоминания, приватно",
        "tagline": "Запоминание слов, приватно",
        "intro": "Decklet — приложение с карточками и интервальными повторениями для iPhone. Ваши заметки остаются на вашем iPhone.",
        "features": [
            ("free", "Учитесь бесплатно и без ограничений", "Интервальные повторения (FSRS) показывают каждую карточку незадолго до того, как вы её забудете. Любое число колод и карточек, без дневного лимита и без рекламы."),
            ("free", "Начать одним касанием", "Виджеты экрана блокировки и главного экрана и кнопка в Пункте управления запускают занятие. Ежедневное напоминание, серия и статистика."),
            ("pro", "Карточки из ваших материалов", "Отсканируйте страницу, выберите фото или PDF-файлы или вставьте заметки. ИИ пишет карточки на вашем iPhone с Apple Intelligence, а вы проверяете их перед сохранением."),
            ("free", "Перенесите свои колоды", "Импорт из других приложений с карточками (.apkg), из текста и CSV. Резервная копия в файл и экспорт любой колоды в CSV."),
        ],
        "pills": ["Без аккаунта", "Без слежки", "Без аналитики", "Работает без сети"],
    },
    "de": {
        "title": "Decklet: Lernkarten privat und offline",
        "tagline": "Lernkarten privat & offline",
        "intro": "Decklet sind Lernkarten mit Spaced Repetition für das iPhone. Deine Notizen bleiben auf deinem iPhone.",
        "features": [
            ("free", "Kostenlos lernen, ohne Limits", "Spaced Repetition (FSRS) zeigt jede Karte kurz bevor du sie vergessen würdest. Beliebig viele Stapel und Karten, kein Tageslimit, keine Werbung."),
            ("free", "Mit einem Tipp starten", "Widgets für Sperr- und Home-Bildschirm und ein Schalter im Kontrollzentrum starten eine Lernrunde. Tägliche Erinnerung, Serie und Statistik."),
            ("pro", "Karten aus deinem Material", "Seite scannen, Fotos oder PDF-Dateien wählen oder Notizen einfügen. Die KI schreibt die Karten auf deinem iPhone mit Apple Intelligence, und du prüfst sie, bevor sie gespeichert werden."),
            ("free", "Deine Stapel mitbringen", "Import aus anderen Karteikarten-Apps (.apkg), aus Text und CSV. Backup in eine Datei und jeden Stapel als CSV exportieren."),
        ],
        "pills": ["Kein Konto", "Kein Tracking", "Keine Analyse", "Funktioniert offline"],
    },
}

BACKUP_FEATURES = [
    ("Encrypted before it leaves", "The backup is encrypted on the computer before it is uploaded. The Drive holds only encrypted data, with a password that never leaves the computer."),
    ("Only its own files", "It uses the Google Drive permission drive.file: it can see only the files and folders it created itself, never anything else in the Drive."),
    ("Nothing goes anywhere else", "There is no Tidelab server. Files go straight from the owner's computer to the owner's Drive. No analytics, no advertising, no sharing."),
    ("Checked, then replaced", "After each weekly copy it reads back a part of the data and restores a few files as a test. Only then does it remove the older copy it made before."),
]

BACKUP_PRIVACY = [
    ("In short", ["Tidelab Backup moves its owner's own files into the owner's own Google Drive. It has no server, collects no data about anyone and shares nothing with anyone."]),
    ("Who uses it", ["Tidelab Backup is a private tool. Only its owner uses it, with their own Google account. It is not offered to other people, and there is no sign-up."]),
    ("Google user data it accesses", [
        "Tidelab Backup asks for one Google permission: https://www.googleapis.com/auth/drive.file. With it, the tool can create files and folders in the signed-in user's Google Drive and read, change and delete only the files and folders it created itself. It cannot see or open any other file in the Drive.",
        "It does not ask for email, contacts, calendar, photos or any other Google data."]),
    ("How the data is used", [
        "Only to store the owner's encrypted backup and copies of the owner's own media files (for example video recordings) in folders it created, to check a stored copy (it reads back a part of the data and a few files), and to delete older copies that it made.",
        "The data is not used for advertising, is not sold, and is not used to develop, improve or train generalized AI or machine-learning models."]),
    ("Where the data is", [
        "The files are in the user's own Google Drive. The backup is encrypted on the computer before upload; the media copies are stored unencrypted, like any other file in that Drive.",
        "The sign-in token that Google issues stays on the owner's computer, in a local configuration file. It is never sent anywhere except to Google."]),
    ("Sharing", ["No data is shared with, sold or transferred to anyone. Nobody except the owner has access. There are no third-party services, analytics or advertising in the tool."]),
    ("Limited Use", ["Tidelab Backup's use and transfer to any other app of information received from Google APIs will adhere to the Google API Services User Data Policy (https://developers.google.com/terms/api-services-user-data-policy), including the Limited Use requirements."]),
    ("Keeping and deleting data", [
        "The Drive keeps only the latest backup copy; older copies are deleted by the tool after a new copy has been checked.",
        "To stop all access, remove Tidelab Backup at https://myaccount.google.com/permissions. To delete the data, delete the folder the tool created in Google Drive."]),
    ("Security", ["Data travels to Google only over encrypted connections (HTTPS). The backup has its own password, which never leaves the owner's computer."]),
    ("Changes", ["If this ever changes, this page is updated first. The date at the top shows the current version."]),
    ("Contact", ["Tidelab · {{SUPPORT_EMAIL}}"]),
]

BACKUP_TERMS = [
    ("What it is", ["Tidelab Backup is a private tool that its owner runs for their own use. It is not offered, sold or licensed to anyone else."]),
    ("Google account", ["Using it needs a Google account; Google's Terms of Service (https://policies.google.com/terms) apply to Google Drive. The stored files count towards the account's Drive storage."]),
    ("No warranty", ["The tool is provided \"as is\", without any warranty. Keep other copies of important data. To the extent the law allows, there is no liability for lost or damaged data."]),
    ("Stopping", ["Access can be removed at any time at https://myaccount.google.com/permissions."]),
    ("Changes", ["These terms may be updated when the tool changes. The date at the top shows the current version."]),
    ("Contact", ["Tidelab · {{SUPPORT_EMAIL}}"]),
]

# ---------------------------------------------------------------- rendering


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def rich(text: str) -> str:
    """Escapes a paragraph, links https:// addresses and the support e-mail."""
    out = re.sub(r"https://[^\s<]+[^\s<.,;)]", lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', esc(text))
    return re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]*\w", lambda m: f'<a href="mailto:{m.group(0)}">{m.group(0)}</a>', out)


class Site:
    def __init__(self, config: dict, legal: dict):
        self.config = config
        self.legal = legal
        self.files: dict[str, str] = {}

    def fill(self, text: str) -> str:
        for key, name in (("support_email", "SUPPORT_EMAIL"), ("operator_name", "OPERATOR_NAME")):
            if self.config.get(key):
                text = text.replace("{{" + name + "}}", self.config[key])
        return text

    def shell(self, path: str, lang: str, title: str, crumb: str, langs: dict | None, body: str, description: str) -> None:
        """One page. path is relative to the site root, e.g. 'decklet/ru/privacy/index.html'."""
        root = "../" * path.count("/")
        root = root or "./"
        top = [f'<a class="brand" href="{root}"><img src="{root}assets/tidelab.svg" alt="" width="32" height="32">Tidelab</a>']
        if crumb:
            top[0] = top[0].replace("</a>", f'</a><span class="crumb">/ {crumb}</span>')
            top[0] = f'<div class="brand-row">{top[0]}</div>'
        if langs:
            items = [f'<span aria-current="true">{code.upper()}</span>' if code == lang else f'<a href="{href}" hreflang="{code}" lang="{code}">{code.upper()}</a>'
                     for code, href in langs.items()]
            top.append(f'<nav class="langs" aria-label="Language">{"".join(items)}</nav>')
        page = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F6F4F0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#100E1A" media="(prefers-color-scheme: dark)">
<meta name="description" content="{esc(description)}">
<title>{esc(title)}</title>
<link rel="icon" href="{root}assets/tidelab.svg" type="image/svg+xml">
<link rel="stylesheet" href="{root}assets/site.css">
</head>
<body>
<div class="wrap">
<header class="top">{"".join(top)}</header>
<main>
{body}
</main>
<footer><p>© {YEAR} Tidelab · <a href="mailto:{{{{SUPPORT_EMAIL}}}}">{{{{SUPPORT_EMAIL}}}}</a></p><p>{esc(UI[lang]["footer"])}</p></footer>
</div>
</body>
</html>
"""
        self.files[path] = self.fill(page)

    def document(self, title: str, updated_label: str, updated: str, sections: list, tabs: str) -> str:
        parts = [tabs, f"<h1>{esc(title)}</h1>", f'<p class="updated">{esc(updated_label)}: {updated}</p>']
        for i, (heading, paragraphs) in enumerate(sections):
            inner = f"<h2>{esc(heading)}</h2>" + "".join(f"<p>{rich(self.fill(p))}</p>" for p in paragraphs)
            parts.append(f'<section class="card summary">{inner}</section>' if i == 0 else f"<section>{inner}</section>")
        return '<article class="doc">' + "\n".join(parts) + "</article>"

    # ---- pages

    def home(self) -> None:
        ui = UI["en"]
        d = DECKLET["en"]
        decklet_name, decklet_links = "Decklet", ""
        if self.with_decklet:
            decklet_name = '<a href="decklet/">Decklet</a>'
            decklet_links = (f'<p class="links"><a href="decklet/">{esc(ui["about"])}</a><a href="decklet/privacy/">Privacy Policy</a>'
                             '<a href="decklet/support/">Support</a><a href="decklet/terms/">Terms of Use</a></p>')
        body = f"""<section class="hero">
<h1>Small apps, made with care.</h1>
<p class="lead">Tidelab is a small independent studio that makes focused apps for iPhone. Our apps keep your data on your device: no tracking, no ads, and no account unless an app really needs one.</p>
</section>
<h2 class="section">Apps</h2>
<article class="card app-card">
<picture><source srcset="assets/decklet-icon-dark.png" media="(prefers-color-scheme: dark)"><img class="icon md" src="assets/decklet-icon-light.png" alt="" width="72" height="72"></picture>
<div><h3>{decklet_name}</h3><p>{esc(d["tagline"])}. Flashcards with spaced repetition for iPhone.</p>
<a class="btn" href="{APP_STORE_URL}">Get Decklet on the App Store</a>
{decklet_links}</div>
</article>
<article class="card" style="margin-top:20px">
<h3><a href="chordcard/">ChordParcel</a></h3>
<p>Transpose your own chord sheet. Share the new copy.</p>
<p>In development. Not yet available on the App Store.</p>
<p class="links"><a href="chordcard/privacy/">Privacy Policy</a><a href="chordcard/support/">Support</a></p>
</article>
<h2 class="section">Contact</h2>
<p>Questions, ideas or a bug to report? Write to <a href="mailto:{{{{SUPPORT_EMAIL}}}}">{{{{SUPPORT_EMAIL}}}}</a>.</p>"""
        self.shell("index.html", "en", "Tidelab: small apps, made with care", "", None, body,
                   "Tidelab is a small independent studio that makes focused, private apps for iPhone.")

    def decklet_base(self, lang: str) -> str:
        return "decklet/" if lang == "en" else f"decklet/{lang}/"

    def decklet(self, lang: str) -> None:
        ui, d, legal = UI[lang], DECKLET[lang], self.legal[lang]
        base = self.decklet_base(lang)
        root = "../" * base.count("/")
        cards = []
        for kind, heading, text in d["features"]:
            tag = ui["pro"] if kind == "pro" else ui["free"]
            mark = "✦" if kind == "pro" else "✓"
            cards.append(f'<div class="card feature {kind}"><div class="dot" aria-hidden="true">{mark}</div><h3>{esc(heading)}</h3><p>{esc(text)}</p>'
                         f'<span class="badge" style="margin-top:12px">{esc(tag)}</span></div>' if kind == "pro" else
                         f'<div class="card feature"><div class="dot" aria-hidden="true">{mark}</div><h3>{esc(heading)}</h3><p>{esc(text)}</p></div>')
        links = "".join(f'<a class="btn ghost" href="{k}/">{esc(legal["links"][k])}</a>' for k in KINDS)
        body = f"""<section class="app-hero">
<picture><source srcset="{root}assets/decklet-icon-dark.png" media="(prefers-color-scheme: dark)"><img class="icon lg" src="{root}assets/decklet-icon-light.png" alt="Decklet" width="112" height="112"></picture>
<div><h1>Decklet</h1><p>{esc(d["tagline"])}</p><a class="btn" href="{APP_STORE_URL}">{esc(ui["soon"])}</a></div>
</section>
<p style="font-size:1.15rem;margin:22px 0 0">{esc(d["intro"])}</p>
<ul class="pills">{"".join(f"<li>{esc(p)}</li>" for p in d["pills"])}</ul>
<div class="grid" style="margin-top:28px">{"".join(cards)}</div>
{('<h2 class="section">Start with your own cards</h2><p><a href="import-csv/">How to import a spreadsheet as flashcards</a> · <a href="sample-travel.csv" download>Try a five-card CSV sample</a></p>' if lang == 'en' else '')}
<h2 class="section">{esc(ui["info"])}</h2>
<div class="row" style="margin-top:0">{links}</div>
{('<p><a href="offline-flashcards/">Move a small deck without an account</a> · <a href="exam-flashcards/">Turn exam notes into a first deck</a></p>' if lang == 'en' else '')}<p style="margin-top:18px">{esc(ui["contact"])}: {rich(self.fill("{{SUPPORT_EMAIL}}"))}</p>"""
        self.shell(base + "index.html", lang, d["title"], "Decklet", None, body, d["intro"])

    def decklet_doc(self, lang: str, kind: str) -> None:
        legal = self.legal[lang]
        base = self.decklet_base(lang)
        path = f"{base}{kind}/index.html"
        tabs = '<nav class="tabs" aria-label="Decklet">' + "".join(
            f'<span aria-current="page">{esc(legal["links"][k])}</span>' if k == kind else f'<a href="../{k}/">{esc(legal["links"][k])}</a>'
            for k in KINDS) + "</nav>"
        body = self.document(legal[f"{kind}_title"], legal["updated"], self.legal_updated, legal[kind], tabs)
        crumb = f'<a href="../">Decklet</a>'
        self.shell(path, lang, legal[f"{kind}_title"], crumb, None, body, legal[f"{kind}_title"])

    def csv_guide(self) -> None:
        body = f'''<article class="doc">
<h1>Turn a spreadsheet into flashcards on your iPhone</h1>
<p>From the small team that makes Decklet · 7 November 2026</p>
<p>You do not need AI to turn a vocabulary list into study cards. A two-column spreadsheet is enough: put a question or word in the first column and its answer in the second.</p>
<h2>Make a small file first</h2>
<p>Start with five rows. Keep each card focused on one thing you want to recall. Save the sheet as a UTF-8 CSV file, or use tab-separated text. Decklet reads the first two columns as front and back.</p>
<pre>front,back
hello,bonjour
thank you,merci
please,s'il vous plaît
water,eau
the station,la gare</pre>
<p><a href="../sample-travel.csv" download>Download this five-card example</a>. We wrote these simple travel vocabulary pairs for you to try; no sign-up is needed.</p>
<h2>Import and check</h2>
<ol><li>Open Decklet and choose Import, then CSV or TSV.</li>
<li>Choose the file, or paste the two-column text.</li>
<li>If the first row contains column names, turn on “First row is a header”.</li>
<li>Check the preview and the number of skipped rows. Give the deck a name, then tap Import.</li>
<li>Start studying and check the answer before you rate your recall.</li></ol>
<h2>If a row looks wrong</h2>
<p>Check that both columns have text. A comma inside a question or answer needs CSV quotes; exporting from your spreadsheet handles that for you. Try a five-row file before importing a larger collection, and keep the original file.</p>
<h2>Share the material you choose</h2>
<p>You can export a deck as CSV and share that file using the iPhone share sheet. The person receiving it can inspect it in a spreadsheet or import it into Decklet. Share only material you created or have permission to distribute; leave out personal information.</p>
<h2>What is free</h2>
<p>Manual cards, CSV import and spaced repetition are free in Decklet, without a daily card limit. AI card creation is an optional Pro feature and is not needed for this guide.</p>
<p><a class="btn" href="{APP_STORE_URL}">Get Decklet on the App Store</a></p>
<p><a href="../">About Decklet</a> · <a href="../privacy/">Privacy</a> · <a href="../support/">Help</a></p>
</article>'''
        self.shell("decklet/import-csv/index.html", "en", "Import CSV flashcards on iPhone · Decklet", '<a href="../">Decklet</a>', None, body,
                   "A practical guide to importing a two-column CSV or TSV vocabulary list into Decklet on iPhone, with a free five-card sample.")
        self.files["decklet/sample-travel.csv"] = "front,back\nhello,bonjour\nthank you,merci\nplease,s'il vous plaît\nwater,eau\nthe station,la gare\n"

    def use_case_guides(self) -> None:
        guides = json.loads((HERE / "use_cases.json").read_text(encoding="utf-8"))
        for guide in guides:
            body = '<article class="doc">' + f'<h1>{esc(guide["heading"])}</h1>'
            body += '<p>From the small team at Tidelab that makes Decklet · 9 November 2026</p>'
            body += f'<p>{esc(guide["intro"])}</p>'
            for section in guide["sections"]:
                body += f'<h2>{esc(section["heading"])}</h2>'
                body += ''.join(f'<p>{esc(p)}</p>' for p in section.get("paragraphs", []))
                if "steps" in section:
                    body += '<ol>' + ''.join(f'<li>{esc(p)}</li>' for p in section["steps"]) + '</ol>'
                if "sample" in section:
                    body += f'<pre style="white-space:pre-wrap;overflow-wrap:anywhere">{esc(section["sample"])}</pre>'
            body += (f'<p><a href="/decklet/{esc(guide["sample_file"])}" download>Download the five-card example</a></p>'
                     f'<p><a class="btn" href="{APP_STORE_URL}">Get Decklet on the App Store</a></p>'
                     '<p><a href="/decklet/import-csv/">CSV import steps</a> · <a href="/decklet/">About Decklet</a> · '
                     '<a href="/decklet/privacy/">Privacy</a> · <a href="/decklet/support/">Help</a></p></article>')
            self.shell(f'decklet/{guide["slug"]}/index.html', 'en', guide["title"],
                       '<a href="../">Decklet</a>', None, body, guide["description"])
            self.files[f'decklet/{guide["sample_file"]}'] = guide["csv"]

    def campaign_guides(self) -> None:
        # No script, cookie or visitor identifier. Each source has its own static URL.
        token = str(self.config.get("campaign_provider_token", ""))
        if token and not re.fullmatch(r"[0-9]+", token):
            raise ValueError("campaign_provider_token must be the numeric pt from an App Store Connect campaign link")
        for slug, code in (("import-csv", "csv"), ("offline-flashcards", "offline"), ("exam-flashcards", "exam")):
            path = f"decklet/{slug}/index.html"
            original = self.files[path]
            canonical = f'<link rel="canonical" href="https://tidelab-apps.github.io/decklet/{slug}/">'
            self.files[path] = original.replace('</head>', canonical + '\n</head>')
            canonical_page = self.files[path]
            if not token:
                continue
            for source, suffix in (("site", ""), ("bsky", "from-bluesky/"), ("masto", "from-mastodon/")):
                campaign = f"wf1{code}{source}"
                url = "https://apps.apple.com/app/apple-store/id6829718725?" + urlencode(
                    {"pt": token, "ct": campaign, "mt": "8"})
                page = canonical_page.replace(APP_STORE_URL, esc(url))
                if suffix:
                    # Preserve all relative assets, sample links and navigation one level deeper.
                    page = re.sub(r'(href|src)="(?!https?:|mailto:|/|#)([^"]*)"',
                                  lambda m: f'{m[1]}="../{m[2]}"', page)
                    page = page.replace('</head>', '<meta name="robots" content="noindex,follow">\n</head>')
                self.files[f"decklet/{slug}/{suffix}index.html"] = page

    def backup(self) -> None:
        cards = "".join(f'<div class="card feature"><div class="dot" aria-hidden="true">✓</div><h3>{esc(h)}</h3><p>{rich(t).replace("drive.file", "<code>drive.file</code>")}</p></div>'
                        for h, t in BACKUP_FEATURES)
        body = f"""<section class="app-hero">
<img class="icon lg" src="../assets/backup-icon.svg" alt="Tidelab Backup" width="112" height="112">
<div><h1>Tidelab Backup</h1><p>Encrypted backups in Google Drive</p><span class="badge">Private tool · not offered to the public</span></div>
</section>
<p style="font-size:1.15rem;margin:22px 0 0">Tidelab Backup keeps an encrypted backup of its owner's computer in the owner's own Google Drive. It runs on a schedule on that computer and makes a new copy every week.</p>
<div class="grid" style="margin-top:28px">{cards}</div>
<h2 class="section">How it works</h2>
<p>The tool signs in to Google once, with the owner's own Google account, and keeps that sign-in on the computer. Each week it uploads only what changed since the last copy, checks the new copy and then removes the older one. Besides the encrypted backup, it can place copies of the owner's own media files, such as video recordings, in a separate folder that it created in the same Drive, so they can be watched there.</p>
<h2 class="section">Who can use it</h2>
<p>Only its owner, with their own Google account. There is no sign-up and no download: the tool is not offered to other people.</p>
<div class="row"><a class="btn ghost" href="privacy/">Privacy Policy</a><a class="btn ghost" href="terms/">Terms of Use</a></div>
<h2 class="section">Contact</h2>
<p>{rich(self.fill("Tidelab · {{SUPPORT_EMAIL}}"))}</p>"""
        self.shell("backup/index.html", "en", "Tidelab Backup: an encrypted backup in your own Google Drive", "Backup", None, body,
                   "Tidelab Backup keeps an encrypted backup of its owner's computer in the owner's own Google Drive, with access only to its own files.")
        for kind, title, sections in (("privacy", "Tidelab Backup Privacy Policy", BACKUP_PRIVACY), ("terms", "Tidelab Backup Terms of Use", BACKUP_TERMS)):
            names = {"privacy": "Privacy Policy", "terms": "Terms of Use"}
            tabs = '<nav class="tabs" aria-label="Tidelab Backup">' + '<a href="../">About</a>' + "".join(
                f'<span aria-current="page">{v}</span>' if k == kind else f'<a href="../{k}/">{v}</a>' for k, v in names.items()) + "</nav>"
            self.shell(f"backup/{kind}/index.html", "en", title, '<a href="../">Backup</a>', None,
                       self.document(title, "Last updated", BACKUP_UPDATED, sections, tabs), title)

    def chordcard_pages(self) -> None:
        """ChordParcel uses the stable paths already linked by its iOS build."""
        data = json.loads((HERE / "chordcard.json").read_text(encoding="utf-8"))
        routes = {"product": "chordcard/", "privacy": "chordcard/privacy/", "support": "chordcard/support/"}
        labels = {"product": "About ChordParcel", "privacy": "Privacy Policy", "support": "Support"}
        for kind, base in routes.items():
            page = data[kind]
            tabs = '<nav class="tabs" aria-label="ChordParcel">' + "".join(
                f'<span aria-current="page">{esc(label)}</span>' if key == kind
                else f'<a href="/{routes[key]}">{esc(label)}</a>'
                for key, label in labels.items()) + '</nav>'
            parts = [tabs, f'<h1>{esc(page["title"])}</h1>']
            if kind == "privacy":
                parts.append(f'<p class="updated">Last updated: {esc(data["updated"])}</p>')
            parts.extend(f'<p>{rich(paragraph)}</p>' for paragraph in page["paragraphs"])
            body = '<article class="doc">' + "\n".join(parts) + '</article>'
            self.shell(base + "index.html", "en", page["title"], '<a href="/chordcard/">ChordParcel</a>',
                       None, body, page["description"])

    def not_found(self) -> None:
        body = '<section class="hero"><h1>Page not found</h1><p class="lead">This page does not exist. <a href="/">Go to the Tidelab home page</a>.</p></section>'
        self.shell("404.html", "en", "Page not found · Tidelab", "", None, body, "Page not found")
        # GitHub Pages serves 404.html for every missing path, so its links must be absolute.
        self.files["404.html"] = self.files["404.html"].replace('href="./', 'href="/').replace('src="./', 'src="/')

    def build(self) -> None:
        self.legal_updated = self.legal_module_updated
        self.home()
        for lang in LANGS if self.with_decklet else ():
            self.decklet(lang)
            for kind in KINDS:
                self.decklet_doc(lang, kind)
        if self.with_decklet:
            self.csv_guide()
            self.use_case_guides()
            self.campaign_guides()
        self.backup()
        self.chordcard_pages()
        self.not_found()


def load_legal(path: Path):
    spec = importlib.util.spec_from_file_location("decklet_legal", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decklet-legal", type=Path, default=DECKLET_LEGAL)
    ap.add_argument("--release", action="store_true")
    args = ap.parse_args()
    if not args.decklet_legal.is_file():
        print(f"PROBLEM: Decklet texts not found: {args.decklet_legal}")
        return 1
    legal = load_legal(args.decklet_legal)
    for lang in LANGS:
        missing = [k for k in KINDS if k not in legal.PAGES[lang]]
        if missing:
            print(f"PROBLEM: Decklet texts for {lang} have no {missing}")
            return 1
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    site = Site(config, legal.PAGES)
    site.legal_module_updated = legal.UPDATED
    # Decklet's legal pages name the operator. Without that name a release goes out without the Decklet pages
    # (home and Backup need no name); a draft build always writes everything.
    site.with_decklet = bool(config.get("operator_name")) or not args.release
    site.build()
    if not site.with_decklet and (HERE / "decklet").is_dir():
        shutil.rmtree(HERE / "decklet")  # generated output, kept in git history
        print("release without Decklet pages: operator_name is not set")
    for rel, text in site.files.items():
        out = HERE / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
    (HERE / ".nojekyll").write_text("", encoding="utf-8")
    left = sorted({m for text in site.files.values() for m in re.findall(r"\{\{[A-Z_]+\}\}", text)})
    print(f"written: {len(site.files)} pages")
    if left:
        print("placeholders left (config.json):", ", ".join(left))
        if args.release:
            print("PROBLEM: --release with placeholders left")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
