# Manuscript

LaTeX source for the FLEX-DBS paper. One source builds both a PDF and a Word document.

```sh
make          # build/flex_dbs.pdf and build/flex_dbs.docx
make pdf      # PDF only
make docx     # DOCX only
make figures  # regenerate figures/fig1_architecture.png and figures/fig4_impedance.png
make watch    # rebuild the PDF on every save (needs: brew install fswatch)
make clean
```

Requires [Tectonic](https://tectonic-typesetting.github.io/) and [pandoc](https://pandoc.org/)
(`brew install tectonic pandoc`). Tectonic downloads the LaTeX packages it needs on first run.
`make figures` also needs Node (for `npx @mermaid-js/mermaid-cli`) and Python 3; the first run
creates `.venv/` with matplotlib.

## Layout

| Path | Contents |
|---|---|
| `main.tex` | Title block and the order of sections |
| `sections/*.tex` | One file per section; edit these |
| `sections/working_notes.tex` | Open items and pending data; remove before submission |
| `refs.bib` | Bibliography |
| `creed.sty` | PDF-only styling (fonts, margins, title format, natbib) |
| `figures/` | Images referenced by `sections/figures.tex` |
| `figures/fig1_architecture.mmd` | Mermaid source for Figure 1 |
| `figures/scripts/fig_impedance.py` | Builds Figure 4 from `../data/impedance/mousehatImpedance.xlsx` |
| `supplements/` | Supplementary files (schematic) |
| `templates/reference.docx` | Word styles applied to the DOCX (copied from `creed_v81_draft.docx`) |
| `templates/elsevier-harvard.csl` | Citation style for the DOCX |

To restyle the DOCX, open `templates/reference.docx` in Word, change the styles (Normal, Heading 1–3,
Title, Subtitle, and so on), and save. pandoc uses only the styles, not the text.

## Citations

Cite with natbib: `\citep{key}` gives "(Author, 2020)" and `\citet{key}` gives "Author (2020)".
Keys live in `refs.bib`. The PDF uses BibTeX with `elsarticle-harv`; the DOCX uses pandoc's
citeproc with the Elsevier Harvard CSL, so both come out in the same author-year style. In the
DOCX the reference list is always placed at the end of the document.

## Keeping the DOCX faithful

pandoc reads the same `.tex` files, so write the body in plain LaTeX: `\section`, lists,
`longtable`, `\includegraphics`, `\emph`/`\textbf`, inline math. In particular:

- Don't define macros for manuscript text. The DOCX build turns macro expansion off, so they
  would not appear in Word.
- Write table column types in full with a trailing `{}`, as in
  `>{\raggedright\arraybackslash{}}p{0.3\linewidth}`. Without the `{}`, pandoc drops the first
  word of each cell.
- A list item that starts with `[` needs braces, `\item {[Pending]}`; otherwise LaTeX
  treats the bracket as the item label.

Section, table and figure numbers are typed by hand in headings and legends. Reviewer comments
from Word are kept as `% COMMENT` lines in the source.
