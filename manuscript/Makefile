# Build the manuscript from main.tex + sections/*.tex.
#   make          PDF and DOCX into build/
#   make pdf      PDF only (tectonic; BibTeX with elsarticle-harv)
#   make docx     DOCX only (pandoc, styled by templates/reference.docx, citations by citeproc)
#   make notes    working notes as a separate PDF (notes.tex)
#   make figures  regenerate the impedance plot and the bench plot (Figure 1 is a static image)
#   make watch    rebuild the PDF whenever a source file changes
#   make clean    remove build/

NAME    := flex_dbs
BUILD   := build
SOURCES := main.tex creed.sty refs.bib $(filter-out sections/working_notes.tex,$(wildcard sections/*.tex)) $(wildcard figures/*.png figures/*.jpg)
CSL     := templates/elsevier-harvard.csl
VENV    := .venv

.PHONY: all pdf docx notes figures watch clean

all: pdf docx notes

pdf: $(BUILD)/$(NAME).pdf
docx: $(BUILD)/$(NAME).docx
notes: $(BUILD)/$(NAME)_notes.pdf

$(BUILD)/$(NAME)_notes.pdf: notes.tex sections/working_notes.tex sections/references.tex creed.sty refs.bib
	@mkdir -p $(BUILD)
	tectonic --outdir $(BUILD) notes.tex
	@mv $(BUILD)/notes.pdf $@
	@echo "Wrote $@"

$(BUILD)/$(NAME).pdf: $(SOURCES)
	@mkdir -p $(BUILD)
	tectonic --outdir $(BUILD) main.tex
	@mv $(BUILD)/main.pdf $@
	@echo "Wrote $@"

$(BUILD)/$(NAME).docx: $(SOURCES) templates/reference.docx $(CSL)
	@mkdir -p $(BUILD)
	pandoc main.tex --from latex-latex_macros --to docx \
		--reference-doc templates/reference.docx \
		--shift-heading-level-by 1 \
		--citeproc --bibliography refs.bib --csl $(CSL) \
		--resource-path . \
		--output $@
	@echo "Wrote $@"

figures: figures/fig4_impedance.png figures/fig5_bench.png

figures/fig4_impedance.png: figures/scripts/fig_impedance.py ../data/impedance/mousehatImpedance.xlsx | $(VENV)
	$(VENV)/bin/python $<

figures/fig5_bench.png: figures/scripts/fig_bench.py $(wildcard ../data/bench/*.jls) | $(VENV)
	$(VENV)/bin/python $<

$(VENV):
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --quiet matplotlib numpy scipy pyjls

watch:
	@command -v fswatch >/dev/null || { echo "watch needs fswatch: brew install fswatch"; exit 1; }
	$(MAKE) pdf
	fswatch -o main.tex refs.bib sections figures | while read _; do $(MAKE) pdf; done

clean:
	rm -rf $(BUILD)
