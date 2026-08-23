# Embedded Systems with STM32

📖 **Read the book online:** <https://SamShue.github.io/Embedded-Systems-Textbook-STM32/>

This repository contains the source for an introductory embedded systems
textbook built around an STMicroelectronics STM32 microcontroller.

The book is written as a [Quarto](https://quarto.org) project and lives in
[`book/`](book/). It can be rendered to a searchable HTML site and/or a PDF.

This is a companion book to "Embedded Systems with the MSP430G2553",
following the same chapter structure, but maintained as a separate
repository since the two books target different microcontroller families
and most chapter content (peripheral registers, memory maps, toolchain) does
not translate directly between them.

## Status

This book is a work in progress. No chapter content has been written yet
&mdash; `book/chapters/*.qmd` are currently placeholders. See
[`book/index.qmd`](book/index.qmd) for the planned table of contents.

## Repository layout

```
book/                       Quarto project (the book itself)
  _quarto.yml                Book configuration (title, chapter list, output formats)
  index.qmd                  Preface / front matter
  chapters/                  One .qmd file per chapter
  images/                    Figures, organized per-chapter (images/ch01, images/ch02, ...)
```

## Installing the required tools

You only need **Quarto** (which bundles Pandoc) to build the book.

### 1. Quarto (required)

- **All platforms:** download an installer from
  <https://quarto.org/docs/get-started/> and follow the platform instructions.
- **Linux (no root/sudo needed):** download the portable tarball and put it
  on your `PATH`:

  ```bash
  curl -sL https://github.com/quarto-dev/quarto-cli/releases/download/v1.10.18/quarto-1.10.18-linux-amd64.tar.gz -o quarto.tar.gz
  tar xzf quarto.tar.gz -C ~/tools    # or any directory you like
  export PATH="$HOME/tools/quarto-1.10.18/bin:$PATH"   # add to ~/.bashrc to persist
  ```
- **macOS (Homebrew):** `brew install --cask quarto`
- **Windows (winget):** `winget install --id Posit.Quarto`

Verify the install:

```bash
quarto check
```

### 2. A PDF engine (optional, only needed for `quarto render --to pdf`)

```bash
quarto install tinytex
```

## Building the book

From the `book/` directory:

```bash
cd book

# Render to HTML (output goes to book/_book/)
quarto render --to html

# Render to PDF (requires a LaTeX install, see above)
quarto render --to pdf

# Render everything configured in _quarto.yml (html + pdf)
quarto render
```

To preview the book locally with live-reload while editing:

```bash
cd book
quarto preview
```

Rendered output is written to `book/_book/` and is not checked into version
control.

## Publishing

The book is published to GitHub Pages at
<https://SamShue.github.io/Embedded-Systems-Textbook-STM32/>. A GitHub
Action ([`.github/workflows/publish.yml`](.github/workflows/publish.yml))
automatically re-renders and re-publishes the site (to the `gh-pages`
branch) on every push to `main` &mdash; no manual steps are needed after
merging a change.

If you ever need to publish manually from your own machine instead (e.g. to
test something before pushing), run:

```bash
cd book
quarto publish gh-pages
```

## Editing content

- Each chapter is a single `.qmd` file in `book/chapters/`, named
  `NN-slug.qmd` (e.g. `03-gpio.qmd`). Chapter order and grouping into parts
  is controlled by the `book.chapters` list in `book/_quarto.yml`.
- Chapters use plain Markdown, with a YAML `title:` front matter block.
  **Use `##` (not `#`) for the top-level sections within a chapter** &mdash;
  the chapter title itself comes from the YAML `title:`, so body sections
  need to start one level down in order for section/figure numbering to nest
  correctly under the chapter (e.g. "1.1 Learning Objectives", "Figure 1.2").
  See the [Quarto Markdown Basics guide](https://quarto.org/docs/authoring/markdown-basics.html)
  for formatting help.
- Figures should live under `book/images/chNN/` and be referenced with a
  Quarto figure ID for automatic numbering and cross-referencing, e.g.:

  ```markdown
  ![Caption text](../images/ch03/image30.png){#fig-ch03-3-2}
  ```

  You can cross-reference a figure elsewhere in the same chapter with
  `@fig-ch03-3-2`, which Quarto renders as an auto-numbered, clickable
  reference (e.g. "Figure 3.2").
- Code listings use fenced code blocks (` ```c ... ``` `) for syntax
  highlighting.
