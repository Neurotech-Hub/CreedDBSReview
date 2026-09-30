# Build the manuscript from main.tex + sections/*.tex.
#   make          PDF and DOCX into build/
#   make pdf      PDF only (tectonic; BibTeX with elsarticle-harv)
#   make docx     DOCX only (pandoc, styled by templates/reference.docx, citations by citeproc)
#   make figures  regenerate the Mermaid diagram and the impedance plot
#   make watch    rebuild the PDF whenever a source file changes
#   make clean    remove build/

NAME    := flex_dbs
BUILD   := build
SOURCES := main.tex creed.sty refs.bib $(wildcard sections/*.tex) $(wildcard figures/*.png figures/*.jpg)
CSL     := templates/elsevier-harvard.csl
VENV    := .venv

.PHONY: all pdf docx figures watch clean

all: pdf docx

pdf: $(BUILD)/$(NAME).pdf
docx: $(BUILD)/$(NAME).docx

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

figures: figures/fig1_architecture.png figures/fig4_impedance.png

figures/fig1_architecture.png: figures/fig1_architecture.mmd
	npx -y @mermaid-js/mermaid-cli@11 -i $< -o $@ -s 3 -b white

figures/fig4_impedance.png: figures/scripts/fig_impedance.py ../data/impedance/mousehatImpedance.xlsx | $(VENV)
	$(VENV)/bin/python $<

$(VENV):
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --quiet matplotlib

watch:
	@command -v fswatch >/dev/null || { echo "watch needs fswatch: brew install fswatch"; exit 1; }
	$(MAKE) pdf
	fswatch -o main.tex refs.bib sections figures | while read _; do $(MAKE) pdf; done

clean:
	rm -rf $(BUILD)
