
import sys
import html
import re
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextBrowser,
    QDialog, QSlider, QComboBox
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont


SETTINGS = QSettings("AISearch", "AISearch")

LANGS = {
    "fa": {
        "title": "جستجوی هوشمند اینترنت",
        "placeholder": "سؤالت را اینجا بنویس...",
        "search": "جستجو",
        "settings": "تنظیمات",
        "ready": "آماده جستجو",
        "searching": "در حال جستجو و بررسی صفحات...",
        "empty": "سؤال را بنویس.",
        "error": "خطا در جستجو یا اتصال اینترنت",
        "size": "اندازه نوشته",
        "close": "ذخیره و بستن",
        "language": "زبان برنامه",
        "sources": "منابع",
        "noresult": "نتیجه مناسبی پیدا نشد.",
        "answer": "پاسخ"
    },
    "en": {
        "title": "Smart Internet Search",
        "placeholder": "Type your question...",
        "search": "Search",
        "settings": "Settings",
        "ready": "Ready",
        "searching": "Searching and reading websites...",
        "empty": "Enter a question.",
        "error": "Search or connection error",
        "size": "Text size",
        "close": "Save and close",
        "language": "App language",
        "sources": "Sources",
        "noresult": "No useful results found.",
        "answer": "Answer"
    },
    "ar": {
        "title": "البحث الذكي في الإنترنت",
        "placeholder": "اكتب سؤالك هنا...",
        "search": "بحث",
        "settings": "الإعدادات",
        "ready": "جاهز",
        "searching": "جارٍ البحث وقراءة المواقع...",
        "empty": "اكتب السؤال.",
        "error": "خطأ في البحث أو الاتصال",
        "size": "حجم النص",
        "close": "حفظ وإغلاق",
        "language": "لغة البرنامج",
        "sources": "المصادر",
        "noresult": "لم يتم العثور على نتائج مفيدة.",
        "answer": "الإجابة"
    }
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0.0.0 "
        "Safari/537.36"
    )
}


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def google_search(query):
    results = []

    # جستجوی DuckDuckGo
    try:
        with DDGS() as engine:
            items = list(
                engine.text(
                    query,
                    max_results=12
                )
            )

            for item in items:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("body", ""),
                    "url": item.get("href", "")
                })

    except Exception:
        pass

    return results


def read_pages(results):
    session = requests.Session()
    session.headers.update(HEADERS)

    for item in results:

        url = item.get("url", "")

        if not url:
            continue

        try:
            response = session.get(
                url,
                timeout=9
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for element in soup.select(
                "script, style, nav, footer, "
                "header, aside, iframe, noscript, "
                "form, svg"
            ):
                element.decompose()

            text = clean_text(
                soup.get_text(" ", strip=True)
            )

            item["page_text"] = text[:12000]

        except Exception:
            item["page_text"] = ""

    return results


def tokenize(text):
    text = text.lower()

    words = re.findall(
        r"[\w\u0600-\u06FF]+",
        text
    )

    stopwords = {
        "the", "and", "for", "that", "with",
        "from", "this", "what", "when", "where",
        "which", "about", "how", "are", "is",
        "was", "were", "to", "of", "in", "on",
        "it", "a", "an", "as", "by", "or",
        "be", "can", "do", "does", "did",
        "why", "who", "will", "would", "has",
        "have", "had", "not",

        "و", "در", "از", "به", "که", "این",
        "آن", "را", "با", "برای", "چه", "چرا",
        "چگونه", "کجا", "کی", "است", "بود",
        "هست", "های", "یک", "یا", "اگر",
        "تا", "می", "شود", "شد", "هم", "اما",
        "درباره", "روی", "پس", "باید",

        "في", "من", "إلى", "على", "عن",
        "هذا", "هذه", "هو", "هي", "ما",
        "كيف", "لماذا", "ماذا", "كان",
        "أن", "و", "أو", "مع", "ذلك",
        "التي", "الذي", "هل", "هناك"
    }

    return [
        w for w in words
        if w not in stopwords and len(w) > 1
    ]


def sentence_split(text):
    return re.split(
        r"(?<=[.!?؟。])\s+",
        text
    )


def make_answer(question, results):

    question_words = set(
        tokenize(question)
    )

    candidates = []

    for item in results:

        title = item.get("title", "")
        snippet = item.get("snippet", "")
        page = item.get("page_text", "")

        combined = (
            title + ". " +
            snippet + ". " +
            page
        )

        sentences = sentence_split(
            combined
        )

        for sentence in sentences:

            sentence = clean_text(sentence)

            if len(sentence) < 35:
                continue

            words = set(
                tokenize(sentence)
            )

            overlap = (
                len(words & question_words)
            )

            if overlap == 0:
                continue

            score = overlap

            # تطبیق بیشتر با کلمات سؤال
            score += overlap * 1.8

            # جمله‌های موجود در متن واقعی سایت
            if sentence in page:
                score += 1.5

            # جملات طولانی و بی‌ربط حذف شوند
            if len(sentence) > 550:
                score -= 2

            candidates.append({
                "sentence": sentence,
                "score": score,
                "url": item.get("url", "")
            })

    # مرتب‌سازی بهترین جملات
    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    selected = []
    seen = set()

    for item in candidates:

        sentence = item["sentence"]

        normalized = sentence.lower()

        if normalized in seen:
            continue

        seen.add(normalized)

        selected.append(sentence)

        if len(selected) >= 7:
            break

    if selected:

        return "\n\n".join(selected)

    # اگر تطبیق کلمات جواب نداد،
    # از متن نتایج استفاده می‌کنیم
    fallback = []

    for item in results:

        snippet = item.get("snippet", "")

        if snippet and len(snippet) > 30:
            fallback.append(snippet)

        page = item.get("page_text", "")

        if page and len(page) > 100:
            fallback.append(page[:500])

        if len(fallback) >= 5:
            break

    if fallback:
        return "\n\n".join(fallback)

    return "No useful text was found."


def search_engine_answer(question, results):

    answer = make_answer(
        question,
        results
    )

    return answer


class AIWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.lang = SETTINGS.value(
            "language", "fa"
        )

        self.font_size = int(
            SETTINGS.value("font_size", 14)
        )

        self.setWindowTitle(
            "AI Search"
        )

        self.resize(950, 720)

        self.setStyleSheet("""
            QWidget {
                background-color: #17191e;
                color: #f1f1f1;
                font-family: Tahoma;
            }

            QLineEdit {
                background-color: #252830;
                border: 1px solid #444955;
                border-radius: 15px;
                padding: 15px;
                color: white;
            }

            QPushButton {
                background-color: #3478f6;
                border: none;
                border-radius: 12px;
                padding: 12px;
                color: white;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #2564d7;
            }

            QTextBrowser {
                background-color: #20232a;
                border: none;
                border-radius: 15px;
                padding: 15px;
            }

            QComboBox {
                background-color: #252830;
                padding: 8px;
                border-radius: 8px;
            }
        """)

        self.main = QVBoxLayout(self)

        self.main.setSpacing(15)

        self.main.setContentsMargins(
            25, 20, 25, 20
        )

        self.top = QHBoxLayout()

        self.title = QLabel(
            "AI Search"
        )

        self.title.setFont(
            QFont("Arial", 24, QFont.Bold)
        )

        self.settings_button = QPushButton()

        self.settings_button.clicked.connect(
            self.open_settings
        )

        self.top.addWidget(
            self.title
        )

        self.top.addStretch()

        self.top.addWidget(
            self.settings_button
        )

        self.main.addLayout(
            self.top
        )

        self.subtitle = QLabel()

        self.subtitle.setAlignment(
            Qt.AlignCenter
        )

        self.subtitle.setFont(
            QFont("Tahoma", 14)
        )

        self.main.addWidget(
            self.subtitle
        )

        self.input = QLineEdit()

        self.input.setFont(
            QFont("Tahoma", 15)
        )

        self.input.returnPressed.connect(
            self.search
        )

        self.main.addWidget(
            self.input
        )

        self.search_button = QPushButton()

        self.search_button.clicked.connect(
            self.search
        )

        self.main.addWidget(
            self.search_button
        )

        self.status = QLabel()

        self.status.setAlignment(
            Qt.AlignCenter
        )

        self.main.addWidget(
            self.status
        )

        self.results = QTextBrowser()

        self.results.setOpenExternalLinks(
            True
        )

        self.results.setFont(
            QFont(
                "Tahoma",
                self.font_size
            )
        )

        self.main.addWidget(
            self.results
        )

        self.update_language()

    def update_language(self):

        t = LANGS[self.lang]

        self.subtitle.setText(
            t["title"]
        )

        self.input.setPlaceholderText(
            t["placeholder"]
        )

        self.search_button.setText(
            t["search"]
        )

        self.settings_button.setText(
            t["settings"]
        )

        self.status.setText(
            t["ready"]
        )

        if self.lang in ("fa", "ar"):

            self.setLayoutDirection(
                Qt.RightToLeft
            )

            self.input.setLayoutDirection(
                Qt.RightToLeft
            )

            self.input.setAlignment(
                Qt.AlignRight
            )

        else:

            self.setLayoutDirection(
                Qt.LeftToRight
            )

            self.input.setLayoutDirection(
                Qt.LeftToRight
            )

            self.input.setAlignment(
                Qt.Left
            )

    def open_settings(self):

        dialog = QDialog(self)

        dialog.setWindowTitle(
            LANGS[self.lang]["settings"]
        )

        dialog.resize(400, 280)

        layout = QVBoxLayout(
            dialog
        )

        language_label = QLabel(
            LANGS[self.lang]["language"]
        )

        language_combo = QComboBox()

        language_combo.addItem(
            "فارسی", "fa"
        )

        language_combo.addItem(
            "English", "en"
        )

        language_combo.addItem(
            "العربية", "ar"
        )

        index = language_combo.findData(
            self.lang
        )

        if index >= 0:
            language_combo.setCurrentIndex(
                index
            )

        layout.addWidget(
            language_label
        )

        layout.addWidget(
            language_combo
        )

        size_label = QLabel(
            LANGS[self.lang]["size"]
        )

        slider = QSlider(
            Qt.Horizontal
        )

        slider.setMinimum(12)

        slider.setMaximum(24)

        slider.setValue(
            self.font_size
        )

        layout.addWidget(
            size_label
        )

        layout.addWidget(
            slider
        )

        close_button = QPushButton(
            LANGS[self.lang]["close"]
        )

        def save():

            self.lang = (
                language_combo.currentData()
            )

            self.font_size = (
                slider.value()
            )

            SETTINGS.setValue(
                "language",
                self.lang
            )

            SETTINGS.setValue(
                "font_size",
                self.font_size
            )

            self.results.setFont(
                QFont(
                    "Tahoma",
                    self.font_size
                )
            )

            self.update_language()

            dialog.accept()

        close_button.clicked.connect(
            save
        )

        layout.addWidget(
            close_button
        )

        dialog.exec()

    def search(self):

        query = self.input.text().strip()

        if not query:

            self.status.setText(
                LANGS[self.lang]["empty"]
            )

            return

        self.status.setText(
            LANGS[self.lang]["searching"]
        )

        self.results.clear()

        QApplication.processEvents()

        try:

            items = google_search(
                query
            )

            if not items:

                self.status.setText(
                    LANGS[self.lang]["noresult"]
                )

                return

            items = read_pages(
                items
            )

            answer = search_engine_answer(
                query,
                items
            )

            answer_html = html.escape(
                answer
            )

            sources_html = ""

            for i, item in enumerate(
                items, 1
            ):

                title = html.escape(
                    item.get("title", "")
                )

                link = html.escape(
                    item.get("url", ""),
                    quote=True
                )

                if not link:
                    continue

                sources_html += f"""
                <p>
                <a href="{link}">
                {i}. {title}
                </a>
                </p>
                """

            page = f"""
            <div style="
                line-height:2;
                padding:10px;
            ">

                <h2>
                {LANGS[self.lang]["answer"]}
                </h2>

                <p style="
                    white-space:pre-wrap;
                    line-height:2;
                ">
                {answer_html}
                </p>

                <hr>

                <h3>
                {LANGS[self.lang]["sources"]}
                </h3>

                {sources_html}

            </div>
            """

            self.results.setHtml(
                page
            )

            self.status.setText(
                "پاسخ آماده شد"
                if self.lang == "fa"
                else "Answer ready"
                if self.lang == "en"
                else "تم إعداد الإجابة"
            )

        except Exception as e:

            self.status.setText(
                LANGS[self.lang]["error"]
            )

            self.results.setHtml(
                "<p>خطا در دریافت اطلاعات.</p>"
            )


app = QApplication(sys.argv)

window = AIWindow()

window.show()

sys.exit(app.exec())
