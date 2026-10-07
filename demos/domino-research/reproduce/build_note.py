"""Typeset the research note from the archived numbers: uv run --locked python demos/domino-research/reproduce/build_note.py  (needs XeLaTeX)."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from scripts import texplot  # noqa: E402

R = json.loads((HERE / 'reference/results.json').read_text())
a = [int(x) for x in R['counts']['transfer_matrix_n0_to_16']]
g, fc = R['guess'], R['finite_check']
assert g['coefficients'] == ['4', '-1'] and g['holdout_ok'] and fc['proof_by_finite_check'] and R['closed_form_matches_n0_to_60']
S3 = math.sqrt(3)

ax = texplot.Axis('$n$', 'ratio $a(n+1)/a(n)$', height='4.6cm', xmin=0, xmax=15, ymin=2.9, ymax=3.95, legend=None)
ax.line(list(range(16)), [a[n + 1] / a[n] for n in range(16)], marks='*').hline(2 + S3)
ax.label(15, 2 + S3, '$2+\\sqrt3$', color='muted', anchor='north east', dx='0pt', dy='-4pt')
FIG = texplot.figure_env(ax.tex(), 'The ratio of consecutive terms against the limit $2+\\sqrt3\\approx3.7321$, the larger root of $x^2-4x+1$.', label='fig:ratio')

rows = ''.join(f'{n} & {a[n]:,} & {"" if n < 2 else f"{4 * a[n - 1] - a[n - 2]:,}"} \\\\\n'.replace(',', '\\,') for n in range(0, 11))
TEX = r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.6cm]{geometry}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{newtxtext,newtxmath}
\usepackage{booktabs,caption,xcolor,needspace}
\usepackage[hidelinks]{hyperref}
''' + texplot.PREAMBLE + r'''
\captionsetup{font=small,labelfont=bf,labelsep=period,justification=centering}
\captionsetup[table]{position=above,skip=5pt}\captionsetup[figure]{position=below,skip=4pt}
\linespread{1.1}\setlength{\parindent}{1.4em}\setlength{\parskip}{2pt}
\theoremstyle{plain}\newtheorem{thm}{Theorem}
\renewcommand{\proofname}{Proof}
\title{\bfseries Counting domino tilings of a $3\times 2n$ rectangle\\[2pt]\large a worked case of research mode: guess, test, prove twice}
\author{}\date{}
\begin{document}
\maketitle\vspace{-2.5em}
\begin{abstract}\noindent
Let $a(n)$ be the number of ways to tile a $3\times 2n$ board with dominoes. The problem has no answer key in this case file, so every claim carries its own evidence. Counts from three independent methods agree up to $n=16$. A recurrence guessed from 13 terms survives four held-out terms and an exhaustive check to $n=60$, and is then proved in two independent ways: by a column decomposition and by an order bound plus a finite check. The result is classical; the point of the case is the workflow and the honest labelling of each step.
\end{abstract}

\section{Result}
\begin{thm}\label{thm:main}
$a(0)=1$, $a(1)=3$ and $a(n)=4a(n-1)-a(n-2)$ for $n\ge2$. Equivalently
\[a(n)=\frac{3+\sqrt3}{6}\,(2+\sqrt3)^n+\frac{3-\sqrt3}{6}\,(2-\sqrt3)^n,\qquad \frac{a(n+1)}{a(n)}\to2+\sqrt3 .\]
\end{thm}
The sequence $1,3,11,41,153,\dots$ is OEIS \href{https://oeis.org/A001835}{A001835} shifted by one index; the case did not search the literature further, and makes no claim of novelty.

\section{How it was found}
\textbf{Three independent counts.} A backtracking program fills the first free cell of a board, a transfer matrix over the $2^3=8$ column profiles counts tilings by matrix powers, and the coupled recurrences of Section~3 count them by induction. Backtracking and the transfer matrix agree for $n\le5$ (the six boards $3\times0$ to $3\times10$); the transfer matrix and the recurrences agree for $n\le16$. Boards with one corner removed agree between backtracking and the recurrence for $1\le m\le8$.

\textbf{Guess, then test.} From $a(0),\dots,a(12)$ an exact search finds a recurrence of order 2 with coefficients $(4,-1)$: eleven equations, two unknowns. No polynomial of degree $\le8$ fits (the growth is exponential, Figure~\ref{fig:ratio}). Held out from the fit, $a(13),\dots,a(16)$ all satisfy the recurrence, and an exhaustive search over $2\le n\le60$ finds no counterexample.

\begin{table}[htbp]\centering\small
\begin{tabular}{rrr}\toprule
$n$ & $a(n)$ & $4a(n-1)-a(n-2)$\\\midrule
''' + rows + r'''\bottomrule\end{tabular}
\caption{The first terms and the guessed recurrence.}\end{table}
''' + FIG + r'''
\section{Proof A: decomposing the board}
Let $A_m$ be the number of tilings of the $3\times m$ board and $B_m$ the number for the same board with one corner cell removed; set $A_0=1$, $A_1=0$, $B_0=0$, $B_1=1$.

\emph{$A_m=A_{m-2}+2B_{m-1}$.} Look at the three cells of the leftmost column. Either all three are covered by horizontal dominoes, which leaves a $3\times(m-2)$ board; or a vertical domino covers the top two cells, which forces a horizontal domino on the bottom cell and leaves a $3\times(m-1)$ board with its bottom-left corner removed; or the mirror image of that case. These cases are exhaustive and disjoint.

\emph{$B_m=A_{m-1}+B_{m-2}$} (corner cell $(3,1)$ removed). The two remaining cells of the first column are covered by one vertical domino, leaving a full $3\times(m-1)$ board; or by two horizontal dominoes, which forces a horizontal domino on the third cell of the second column and leaves a $3\times(m-2)$ board with a corner removed.

Eliminating $B$: $2B_{m-1}=A_m-A_{m-2}$ and $B_{m-1}=A_{m-2}+B_{m-3}$ give $A_m=4A_{m-2}-A_{m-4}$ for $m\ge4$. With $a(n)=A_{2n}$ this is Theorem~\ref{thm:main}. The closed form follows from the roots $2\pm\sqrt3$ of $x^2-4x+1$ and the values $a(0),a(1)$, and the limit of the ratio from $|2-\sqrt3|<1$. \qed

\section{Proof B: an order bound and a finite check}
The number of tilings of $3\times m$ is $(T^m)_{00}$ for the $8\times8$ column-profile matrix $T$, so $a(n)=(T^{2n})_{00}$ is annihilated by a monic polynomial $P(E)$ of degree at most 8 in the shift $E$ (Cayley--Hamilton for $T^2$). Let $Q(E)=E^2-4E+1$ and $d=Q(E)a$. Polynomials in $E$ commute, so $P(E)d=Q(E)P(E)a=0$: the difference $d$ obeys the same monic recurrence of order $\le8$, and a sequence like that vanishes once its first 8 terms do. Eight consecutive equations, $a(0),\dots,a(9)$, hold; hence $d\equiv0$. This proof does not use Proof~A and is the template implemented by \texttt{check\_recurrence} with \texttt{order\_bound=8}.

\section{Confidence record}
\begin{table}[htbp]\centering\small
\begin{tabular}{p{6.2cm}p{4.2cm}p{3.6cm}}\toprule
Statement & Evidence & Level\\\midrule
$a(n)$ for $n\le5$ & backtracking, transfer matrix, recurrences agree & checked to $n=5$, three methods\\
$a(n)$ for $n\le16$ & transfer matrix and recurrences agree & checked to $n=16$, two methods\\
$a(n)=4a(n-1)-a(n-2)$ for all $n$ & Proof A; Proof B; held-out terms; exhaustive to $n=60$ & proved (two independent proofs)\\
closed form and growth rate & algebra from the recurrence & proved\\
no polynomial formula & degree $\le8$ search; exponential growth & proved by growth\\
novelty & OEIS A001835 lists the sequence & not claimed\\\bottomrule\end{tabular}
\caption{What each statement rests on, using the confidence ladder of the research-mode guide.}\end{table}

\section{Routes tried}
Three routes were recorded with the route-graph tool: (i) guess a linear recurrence from data and test it on held-out terms, which survived and became Proof~B; (ii) guess a polynomial formula, which was killed because the growth is exponential; (iii) prove the recurrence from the column decomposition, which was chosen as the main proof and cross-checked against backtracking. The partial result ``eight consecutive equations prove the recurrence'' was kept with the status \emph{proved by finite check}. The lesson written to the project memory reads: when a count looks like a linear recurrence, guess it from data, hold terms out, then prove it twice, from a local decomposition and from an order bound plus a finite check.

\section{Limits}
A case this small shows the workflow, not research strength. The theorem is classical. The searches support the guess; the proofs rest on the case analysis of Section~3 and on the order bound of Section~4, both short enough to check by hand. Nothing here is checked by a proof assistant.

\paragraph{Reproduce.} \texttt{uv run --locked python demos/domino-research/reproduce/explore.py} recomputes every number in a few seconds; \texttt{build\_note.py} typesets this note from the archived record.
\end{document}
'''
if __name__ == '__main__':
    out = HERE / 'paper'
    out.mkdir(exist_ok=True)
    (out / 'main.tex').write_text(TEX)
    xe = shutil.which('xelatex')
    if not xe:
        raise SystemExit('xelatex not found; install TeX Live or use tectonic')
    for _ in range(2):
        res = subprocess.run([xe, '-interaction=nonstopmode', '-halt-on-error', 'main.tex'], cwd=out, capture_output=True, text=True)
        if res.returncode:
            raise SystemExit(res.stdout[-2500:])
    shutil.copyfile(out / 'main.pdf', HERE.parent / 'deliverables/note.pdf')
    print('built deliverables/note.pdf')
