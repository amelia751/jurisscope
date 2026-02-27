# Testing Package

This folder contains:
- **demo-cases/**: Complete set of 16 case documents (GDPR, AI Act, emails, Slack, meeting notes, etc.)
- **TESTING.tex**: LaTeX version of the testing guide

## Converting TESTING.tex to PDF

### Option 1: Online Converter
Upload `TESTING.tex` to: https://www.overleaf.com/project or https://latexbase.com/

### Option 2: Local LaTeX Installation
```bash
# Install LaTeX (macOS)
brew install --cask mactex

# Compile to PDF
pdflatex testing/TESTING.tex
```

### Option 3: Pandoc (if LaTeX installed)
```bash
pandoc TESTING.tex -o TESTING.pdf
```
