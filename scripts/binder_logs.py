"""Printable, user-selected care records; no default care prescriptions."""
from __future__ import annotations

COLUMNS_PER_PAGE = 3
LOG_ROWS = 8
LABELS = {
    "sedum-loves-fire": "Sedum (Love's Fire)",
    "kalanchoe-desert": "Kalanchoe (Desert)",
    "pothos": "Pothos",
    "bird-of-paradise": "Bird of paradise",
    "aquarium-hornwort": "Hornwort",
    "kuhli-loach": "Kuhli loach",
    "cherry-shrimp": "Cherry shrimp",
    "guppy-grass": "Guppy grass",
    "java-moss": "Java moss",
    "anubias-nana": "Anubias nana",
}


def tracked_species(entries: list[dict]) -> list[str]:
    """One column per entry, regardless of how many companion pages it has."""
    return list(dict.fromkeys(item["id"] for item in entries
                              if item["kind"] != "supplemental"))


def paginate_species(species: list[str]) -> list[list[str]]:
    return [species[i:i + COLUMNS_PER_PAGE]
            for i in range(0, len(species), COLUMNS_PER_PAGE)]


def log_page_tex(species: list[str], page_number: int, page_count: int,
                 *, blank: bool = False) -> str:
    if blank:
        if species:
            raise ValueError("blank edition must not receive species names")
        names = [""] * COLUMNS_PER_PAGE
    else:
        if not 1 <= len(species) <= COLUMNS_PER_PAGE:
            raise ValueError("a named log page needs one to three species")
        names = [LABELS[entry] for entry in species]
    # Pad the last named sheet with unused space, never extra species columns.
    count = len(names)
    headers = [r"\NameCell{" + name + "}" for name in names]
    mode = "BLANK EDITION / copy as needed" if blank else f"TRACKED SPECIES / {page_number} of {page_count}"
    header = r"""\newcommand{\Choice}{\raisebox{0pt}{\fbox{\rule{0pt}{5pt}\rule{5pt}{0pt}}}}
\newcommand{\WriteLine}{\rule{\linewidth}{.3pt}}
\newcommand{\NameCell}[1]{\parbox[c][.65in][t]{\linewidth}{\vspace{2pt}\textbf{#1}\par\vfill\WriteLine\par\vspace{10pt}\WriteLine}}
\newcommand{\PreferenceCell}{\parbox[c][2.8in][t]{\linewidth}{\vspace{3pt}
\textbf{Watering frequency}\par
Every \rule{.30in}{.3pt} days \quad\Choice\ N/A\par
\Choice\ Condition-based\par\vspace{4pt}
\textbf{Check / trigger}\par\vspace{9pt}\WriteLine\par\vspace{4pt}
\textbf{Amount / method}\par\vspace{9pt}\WriteLine\par\vspace{4pt}
\textbf{Propagation / breeding}\par
\Choice\ None planned \quad\Choice\ N/A\par
Method / timing:\par\vspace{9pt}\WriteLine\par\vspace{4pt}
\textbf{Light / location}\par\vspace{9pt}\WriteLine}}
\newcommand{\RecordCell}{\parbox[c][.43in][t]{\linewidth}{\vspace{2pt}A/M or Evt \hrulefill\par\vspace{7pt}Obs \hrulefill}}
\newcommand{\WhenCell}{\parbox[c][.43in][t]{\linewidth}{\vspace{2pt}D \hrulefill\par\vspace{7pt}T \hrulefill}}
{\sffamily\bfseries\fontsize{9}{11}\selectfont DRAFT / HANDWRITTEN CARE RECORD / MODE}\par\vspace{4pt}
{\fontsize{24}{27}\selectfont Watering \& aquarium log}\par\vspace{5pt}
{\sffamily\fontsize{9}{11}\selectfont Choose preferences for each species; these are not universal care instructions.
Check condition, moisture, rain and season before watering. Aquarium events are not watering; choose N/A where appropriate.}\par\vspace{5pt}
{\sffamily\fontsize{9}{11}\selectfont Period: \rule{1.2in}{.3pt}\quad Sheet: \rule{.5in}{.3pt}\quad Names / identity: owner-entered or provisional.}\par\vspace{6pt}
\begingroup\sffamily\fontsize{9}{11}\selectfont
\setlength{\tabcolsep}{4pt}\setlength{\arrayrulewidth}{.4pt}
""".replace("MODE", mode)
    table = r"\begin{tabular}{|p{.64in}|" + "p{1.94in}|" * count + "}\n\\hline\n"
    table += r"Species / name & " + " & ".join(headers) + r"\\\hline" + "\n"
    table += r"My plan & " + " & ".join([r"\PreferenceCell"] * count) + r"\\\hline" + "\n"
    row = r"\WhenCell & " + " & ".join([r"\RecordCell"] * count) + r"\\\hline" + "\n"
    footer = r"""\end{tabular}\endgroup\par\vspace{6pt}
{\sffamily\fontsize{9}{11}\selectfont D = date; T = time; A/M = amount / method; Evt = aquarium event; Obs = observation.\par
Leave unperformed actions blank. Record rain, results or propagation updates in Obs.}\par\vspace{6pt}
{\sffamily\fontsize{9}{11}\selectfont Notes: \hrulefill\par\vspace{12pt}\hrulefill}
"""
    return header + table + row * LOG_ROWS + footer
