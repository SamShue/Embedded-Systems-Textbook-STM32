#!/usr/bin/env python3
"""
Convert Word (.docx) chapter drafts stored under Archive/ into
Quarto-flavored Markdown (.qmd) chapters + extracted images for the book/
project.

This is a template adapted from the companion MSP430 textbook repo's
conversion script (see that repo's scripts/convert_docx_to_qmd.py for the
full, battle-tested implementation and the lessons learned writing it).
It is intentionally left mostly empty here since no Word drafts exist yet
for this book -- fill in the `CHAPTERS` list and adjust the regexes/style
names below once a first chapter draft exists and you've inspected its
paragraph styles (see the "Understanding your Word styles" note below).

Requirements (not bundled with this repo, see README.md):
  - pandoc   (https://pandoc.org)
  - LibreOffice ("soffice" on PATH) - only needed if a chapter embeds legacy
    vector images (.wmf / .emf), which LibreOffice is used to rasterize to
    .png since browsers/pdf engines can't render those formats directly.

Usage:
    python3 scripts/convert_docx_to_qmd.py [chapter_number ...]

Understanding your Word styles:
    Run this to see what custom paragraph styles pandoc detects in a draft
    before writing conversion rules for it:

        pandoc -f docx+styles -t markdown "Archive/.../ChapterX.docx" \\
            | grep -o 'custom-style="[^"]*"' | sort -u
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = REPO_ROOT / "Archive"
BOOK = REPO_ROOT / "book"
CHAPTERS_DIR = BOOK / "chapters"
IMAGES_DIR = BOOK / "images"


@dataclass
class Chapter:
    number: int
    slug: str
    title: str
    docx_dir: str
    docx_glob: str = "*.docx"
    references: str | None = None


# Add an entry per chapter once its Word draft exists, e.g.:
# Chapter(1, "introduction", "Introduction", "CH01 - Introduction"),
CHAPTERS: list[Chapter] = []


def find_docx(chapter: Chapter) -> Path:
    d = ARCHIVE / chapter.docx_dir
    matches = sorted(d.glob(chapter.docx_glob))
    if not matches:
        raise FileNotFoundError(f"No .docx found in {d}")
    return matches[0]


def run_pandoc(docx: Path, media_dir: Path) -> str:
    cmd = [
        "pandoc",
        "-f", "docx+styles",
        "-t", "markdown-smart",
        "--wrap=none",
        f"--extract-media={media_dir}",
        str(docx),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def convert_legacy_images(media_dir: Path) -> None:
    """Rasterize .wmf/.emf images to .png alongside the originals using LibreOffice."""
    legacy = list(media_dir.rglob("*.wmf")) + list(media_dir.rglob("*.emf"))
    if not legacy:
        return
    if not shutil.which("soffice"):
        raise RuntimeError(
            "LibreOffice ('soffice') is required to convert legacy .wmf/.emf "
            "images to .png, but was not found on PATH."
        )
    for f in legacy:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "png", "--outdir", str(f.parent), str(f)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


UNESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!<>\"'~^$%&|@])")
SMART_QUOTES = str.maketrans({
    "\u2018": "'", "\u2019": "'",  # single quotes
    "\u201c": '"', "\u201d": '"',  # double quotes
    "\u2013": "-", "\u2014": "-",  # en/em dash
})


def unescape_code(text: str) -> str:
    """Undo pandoc's markdown-special-character escaping and smart-quote
    typography inside literal code (code must keep plain ASCII punctuation)."""
    text = UNESCAPE_RE.sub(r"\1", text)
    return text.translate(SMART_QUOTES)


ASM_OPCODE_RE = re.compile(r"^\s*[a-zA-Z]{2,6}\.[bwBW]\b")


def guess_lang(lines: list[str]) -> str:
    if lines and all(ASM_OPCODE_RE.match(l) or not l.strip() for l in lines):
        return "asm"
    return "c"


def unwrap_style(text: str, style: str) -> str:
    """Remove a `::: {custom-style="..."}` fenced div wrapper, keeping its content inline."""
    pattern = re.compile(
        r'::: \{custom-style="%s"\}\n(.*?)\n\s*:::' % re.escape(style), re.S
    )

    def repl(m: re.Match) -> str:
        lines = [l.strip() for l in m.group(1).split("\n")]
        return " ".join(l for l in lines if l)

    return pattern.sub(repl, text)


def inline_code_style(text: str, style: str) -> str:
    """Convert a `::: {custom-style="..."}` div into inline `code` text."""
    pattern = re.compile(
        r'::: \{custom-style="%s"\}\n\s*(.*?)\n\s*:::' % re.escape(style), re.S
    )
    return pattern.sub(lambda m: f"`{m.group(1).strip()}`", text)


def reindent_braces(lines: list[str], width: int = 4) -> list[str]:
    """Re-derive consistent indentation from `{`/`}` nesting."""
    out = []
    depth = 0
    for raw in lines:
        s = raw.strip()
        if not s:
            out.append("")
            continue
        leading_close = len(re.match(r"^\}*", s).group())
        this_depth = max(depth - leading_close, 0)
        out.append(" " * (width * this_depth) + s)
        depth = max(depth + s.count("{") - s.count("}"), 0)
    return out


def convert_code_divs(text: str) -> str:
    """Merge consecutive `Code`-styled paragraph divs into fenced ```c blocks."""
    lines = text.split("\n")
    out: list[str] = []
    code_buf: list[str] = []

    def flush() -> None:
        if code_buf:
            lang = guess_lang(code_buf)
            cleaned = [unescape_code(l) for l in code_buf]
            if lang == "c":
                cleaned = reindent_braces(cleaned)
            out.append(f"```{lang}")
            out.extend(cleaned)
            out.append("```")
            code_buf.clear()

    i = 0
    n = len(lines)
    while i < n:
        if lines[i].strip() == '::: {custom-style="Code"}':
            i += 1
            while i < n and lines[i].strip() != ":::":
                # Word paragraphs with an added left-indent get read by pandoc
                # as a blockquote (`> `); this is just visual code indentation.
                code_buf.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            i += 1  # skip closing ':::'
            j = i
            while j < n and lines[j].strip() == "":
                j += 1
            if j < n and lines[j].strip() == '::: {custom-style="Code"}':
                i = j
                continue
            flush()
        else:
            out.append(lines[i])
            i += 1
    flush()
    return "\n".join(out)


FIGURE_PATTERN = re.compile(
    r'!\[[^\]]*\]\([^()]*?/media/(?P<file>[^)]+?)\)(?:\{[^}]*\})?\n\n'
    r'\*\*Figure\s+(?P<num>\d+)\.(?P<sub>\d+):\*\*\s*(?P<cap>[^\n]+)'
)
MEDIA_PATH_RE = re.compile(r"\([^()]*?/media/([^)]+)\)")
BRACKET_CITE_RE = re.compile(r"\\\[(\d+)\\\]")


def rewrite_images(text: str, chapter: Chapter) -> str:
    chnum = f"{chapter.number:02d}"

    def fig_repl(m: re.Match) -> str:
        file = re.sub(r"\.(wmf|emf)$", ".png", m.group("file"), flags=re.I)
        label = f"fig-ch{chnum}-{m.group('num')}-{m.group('sub')}"
        cap = m.group("cap").strip()
        return f"![{cap}](../images/ch{chnum}/{file}){{#{label}}}"

    text = FIGURE_PATTERN.sub(fig_repl, text)

    def path_repl(m: re.Match) -> str:
        file = re.sub(r"\.(wmf|emf)$", ".png", m.group(1), flags=re.I)
        return f"(../images/ch{chnum}/{file})"

    text = MEDIA_PATH_RE.sub(path_repl, text)
    return text


HEADING_RE = re.compile(r"^(#{1,5})(\s)")


def demote_headings(text: str) -> str:
    """Shift every heading down one level (H1->H2, etc).

    Chapters use a YAML `title:` for the chapter heading itself, so the
    original H1 section headings need to become H2 to nest properly *under*
    the chapter. This also makes figure/table auto-numbering use the chapter
    number (e.g. "Figure 1.2") instead of a flat, book-wide heading counter.
    """
    out = []
    in_code = False
    for line in text.split("\n"):
        if line.startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if not in_code:
            line = HEADING_RE.sub(r"#\1\2", line)
        out.append(line)
    return "\n".join(out)


def strip_references_section(text: str) -> str:
    return re.split(r"\n#{1,2} References\b.*", text, flags=re.S)[0].rstrip() + "\n"


def convert_chapter(chapter: Chapter) -> None:
    docx = find_docx(chapter)
    print(f"[ch{chapter.number:02d}] converting {docx.relative_to(REPO_ROOT)}")

    with TemporaryDirectory() as tmp:
        media_dir = Path(tmp)
        raw_md = run_pandoc(docx, media_dir)
        convert_legacy_images(media_dir)

        out_img_dir = IMAGES_DIR / f"ch{chapter.number:02d}"
        if out_img_dir.exists():
            shutil.rmtree(out_img_dir)
        out_img_dir.mkdir(parents=True, exist_ok=True)
        src_media = media_dir / "media"
        if src_media.exists():
            for f in sorted(src_media.iterdir()):
                if f.suffix.lower() in (".wmf", ".emf"):
                    continue
                shutil.copy(f, out_img_dir / f.name)

    text = raw_md
    text = strip_references_section(text)
    text = unwrap_style(text, "List Paragraph")
    text = inline_code_style(text, "q-relative")
    text = convert_code_divs(text)
    text = rewrite_images(text, chapter)
    text = BRACKET_CITE_RE.sub(r"[\1]", text)
    text = demote_headings(text)

    if chapter.references:
        text = text.rstrip() + "\n\n## References\n\n" + chapter.references + "\n"

    front_matter = f'---\ntitle: "{chapter.title}"\n---\n\n'
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CHAPTERS_DIR / f"{chapter.number:02d}-{chapter.slug}.qmd"
    out_path.write_text(front_matter + text.strip() + "\n", encoding="utf-8")
    print(f"[ch{chapter.number:02d}] wrote {out_path.relative_to(REPO_ROOT)}")


def main(argv: list[str]) -> int:
    if not shutil.which("pandoc"):
        print("error: pandoc is required but was not found on PATH.", file=sys.stderr)
        return 1

    if not CHAPTERS:
        print(
            "No chapters configured yet -- add entries to the CHAPTERS list "
            "at the top of this script once a Word draft exists under "
            "Archive/.",
            file=sys.stderr,
        )
        return 1

    wanted = {int(a) for a in argv} if argv else None
    for chapter in CHAPTERS:
        if wanted is not None and chapter.number not in wanted:
            continue
        convert_chapter(chapter)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
