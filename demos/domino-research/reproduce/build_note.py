"""Typeset the research note from the archived numbers: uv run --locked python demos/domino-research/reproduce/build_note.py  (uses the pinned Tectonic runtime)."""
from __future__ import annotations

import json
import math
import shutil
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from scripts import texplot  # noqa: E402
from scripts.paper_template import compile_in_place, style_block, check as check_layout  # noqa: E402

def verification_ranges(record: dict) -> tuple[int, int]:
    """Derive comparison coverage from recorded arrays, never from the abstract."""
    methods = {}
    for key, values in record['counts'].items():
        match = re.fullmatch(r'(backtracking|transfer_matrix|coupled_recurrences)_n0_to_(\d+)', key)
        if match:
            if not values or len(values) != int(match[2]) + 1:
                raise ValueError(f'Count range and array length disagree: {key}')
            methods[match[1]] = values
    if set(methods) != {'backtracking', 'transfer_matrix', 'coupled_recurrences'}:
        raise ValueError('Need all three recorded counting methods')
    three = min(map(len, methods.values()))
    if not (methods['backtracking'][:three] == methods['transfer_matrix'][:three]
            == methods['coupled_recurrences'][:three]):
        raise ValueError('Three-method comparison fails inside its recorded overlap')
    two = min(len(methods['transfer_matrix']), len(methods['coupled_recurrences']))
    if methods['transfer_matrix'][:two] != methods['coupled_recurrences'][:two]:
        raise ValueError('Two-method comparison fails inside its recorded overlap')
    return three - 1, two - 1


def count_summary(record: dict) -> str:
    three, two = verification_ranges(record)
    return (f'All three independent counting methods agree for $0\\le n\\le {three}$; '
            f'the transfer matrix and coupled recurrences agree for $0\\le n\\le {two}$.')


R = json.loads((HERE / 'reference/results.json').read_text())
a = [int(x) for x in R['counts']['transfer_matrix_n0_to_16']]
g, fc = R['guess'], R['finite_check']
assert g['coefficients'] == ['4', '-1'] and g['holdout_ok'] and fc['proof_by_finite_check'] and R['closed_form_matches_n0_to_60']
S3 = math.sqrt(3)

ax = texplot.Axis('$n$', 'ratio $a(n+1)/a(n)$', height='4.6cm', width=r'0.78\linewidth', xmin=0, xmax=15, ymin=2.9, ymax=3.95, legend=None)
ax.line(list(range(16)), [a[n + 1] / a[n] for n in range(16)], marks='*').hline(2 + S3)
ax.label(15, 2 + S3, '$2+\\sqrt3$', color='muted', anchor='north east', dx='0pt', dy='-4pt')
FIG = r'\begin{tikzpicture}' + ax.tex() + r'\end{tikzpicture}' + r'\captionof{figure}{Consecutive-term ratios and the proved limit $2+\sqrt3$.}\label{fig:ratio}'

rows = ''.join(f'{n} & {a[n]:,} & {"" if n < 2 else f"{4 * a[n - 1] - a[n - 2]:,}"} \\\\\n'.replace(',', '\\,') for n in range(0, 11))
TEX = r'\newcommand{\PraxisTitle}{Counting domino tilings of a rectangle}' + '\n' + style_block('research') + r'''
\title[Domino tilings of a rectangle]{Counting domino tilings of a $3\times 2n$ rectangle: two proofs of a classical recurrence}
\author{}\date{}
\begin{document}
\begin{abstract}\noindent
Let $a(n)$ be the number of ways to tile a $3\times 2n$ board with dominoes. @@COUNT_SUMMARY@@ A recurrence guessed from 13 terms survives four held-out terms and an exhaustive check to $n=60$, and is then proved in two independent ways: by a column decomposition and by an order bound plus a finite check. The result is classical. We make the local decomposition and the eight-state transfer matrix explicit, distinguishing finite numerical checks from the arguments that establish the recurrence for every board size.
\end{abstract}
\maketitle

\section{Result}
\begin{theorem}\label{thm:main}
$a(0)=1$, $a(1)=3$ and $a(n)=4a(n-1)-a(n-2)$ for $n\ge2$. Equivalently
\[a(n)=\frac{3+\sqrt3}{6}\,(2+\sqrt3)^n+\frac{3-\sqrt3}{6}\,(2-\sqrt3)^n,\qquad \frac{a(n+1)}{a(n)}\to2+\sqrt3 .\]
\end{theorem}
The sequence is classical: $a(n)$ is term $n+1$ of OEIS A001835~\cite{OEIS}, whose indexing starts with $1,1,3,11,41,\ldots$. The proofs below reconstruct this known count and make no novelty claim.

\section{How it was found}
\textbf{Three independent counts.} A backtracking program fills the first free cell of a board, a transfer matrix over the $2^3=8$ column profiles counts tilings by matrix powers, and the coupled recurrences of Section~3 count them by induction. Backtracking and the transfer matrix agree for $0\le n\le@@THREE@@$; the transfer matrix and the recurrences agree for $0\le n\le@@TWO@@$. Boards with one corner removed agree between backtracking and the recurrence for $1\le m\le8$.

\textbf{Guess, then test.} From $a(0),\dots,a(12)$ an exact search finds a recurrence of order 2 with coefficients $(4,-1)$: eleven equations, two unknowns. No polynomial of degree $\le8$ fits these discovery terms. The exponential growth established by Theorem~\ref{thm:main}, rather than the numerical plot in Figure~\ref{fig:ratio} alone, rules out a polynomial formula of any fixed degree. Held out from the fit, $a(13),\dots,a(16)$ all satisfy the recurrence, and an exhaustive search over $2\le n\le60$ finds no counterexample.

\noindent\begin{minipage}{\linewidth}
\begin{minipage}[t]{.39\linewidth}\vspace{0pt}\centering\small
\captionof{table}{Exact counts and the recurrence.}
\begin{tabular}{rrr}\toprule
$n$ & $a(n)$ & $4a(n-1)-a(n-2)$\\\midrule
''' + rows + r'''\bottomrule\end{tabular}
\end{minipage}\hfill\begin{minipage}[t]{.57\linewidth}\vspace{0pt}
''' + FIG + r'''
\end{minipage}\end{minipage}
\FloatBarrier
\section{Proof A: decomposing the board}
\begin{proof}[Proof by decomposition]
Let $A_m$ be the number of tilings of the $3\times m$ board and $B_m$ the number for the same board with one corner cell removed; set $A_0=1$, $A_1=0$, $B_0=0$, $B_1=1$.

\emph{$A_m=A_{m-2}+2B_{m-1}$.} Look at the three cells of the leftmost column. Either all three are covered by horizontal dominoes, which leaves a $3\times(m-2)$ board; or a vertical domino covers the top two cells, which forces a horizontal domino on the bottom cell and leaves a $3\times(m-1)$ board with its bottom-left corner removed; or the mirror image of that case. These cases are exhaustive and disjoint.

\emph{$B_m=A_{m-1}+B_{m-2}$} (corner cell $(3,1)$ removed). The two remaining cells of the first column are covered by one vertical domino, leaving a full $3\times(m-1)$ board; or by two horizontal dominoes, which forces a horizontal domino on the third cell of the second column and leaves a $3\times(m-2)$ board with a corner removed.


Figure~\ref{fig:split} shows the local configurations used in both identities.
The grey cells form the residual board, and the crossed cell is absent.
\begin{figure}[!ht]
\centering
\begin{tikzpicture}[x=.34cm,y=.34cm,dom/.style={draw=main,fill=main!15,line width=.8pt},every node/.style={font=\small}]
\begin{scope}[shift={(0,0)}]
\fill[black!5] (0,0) rectangle (6,3);\draw[step=1,black!25,thin] (0,0) grid (6,3);
\draw[dom] (0,0) rectangle (2,1);
\draw[dom] (0,1) rectangle (2,2);
\draw[dom] (0,2) rectangle (2,3);
\node at (3.0,-.65) {$A_{m-2}$};\end{scope}
\begin{scope}[shift={(10,0)}]
\fill[black!5] (0,0) rectangle (6,3);\draw[step=1,black!25,thin] (0,0) grid (6,3);
\draw[dom] (0,1) rectangle (1,3);
\draw[dom] (0,0) rectangle (2,1);
\node at (3.0,-.65) {$B_{m-1}$};\end{scope}
\begin{scope}[shift={(20,0)}]
\fill[black!5] (0,0) rectangle (6,3);\draw[step=1,black!25,thin] (0,0) grid (6,3);
\draw[dom] (0,0) rectangle (1,2);
\draw[dom] (0,2) rectangle (2,3);
\node at (3.0,-.65) {$B_{m-1}$};\end{scope}
\node[anchor=east] at (-.5,1.5) {$A_m:$};
\begin{scope}[shift={(4,-6)}]
\fill[black!5] (0,0) rectangle (5,3);\draw[step=1,black!25,thin] (0,0) grid (5,3);
\fill[white] (0,0) rectangle (1,1);\draw[black!50] (0,0)--(1,1) (0,1)--(1,0);
\draw[dom] (0,1) rectangle (1,3);
\node at (2.5,-.65) {$A_{m-1}$};\end{scope}
\begin{scope}[shift={(16,-6)}]
\fill[black!5] (0,0) rectangle (5,3);\draw[step=1,black!25,thin] (0,0) grid (5,3);
\fill[white] (0,0) rectangle (1,1);\draw[black!50] (0,0)--(1,1) (0,1)--(1,0);
\draw[dom] (0,1) rectangle (2,2);
\draw[dom] (0,2) rectangle (2,3);
\draw[dom] (1,0) rectangle (3,1);
\node at (2.5,-.65) {$B_{m-2}$};\end{scope}
\node[anchor=east] at (3.5,-4.5) {$B_m:$};
\end{tikzpicture}
\caption{Exhaustive left-boundary cases. The top row shows a full board (drawn at $m=6$); the bottom row shows a corner-removed board (drawn at $m=5$). Coloured rectangles are forced dominoes, not additional choices. The residual counts indicated below each board give the two recurrences.}
\label{fig:split}
\end{figure}

Eliminating $B$: $2B_{m-1}=A_m-A_{m-2}$ and $B_{m-1}=A_{m-2}+B_{m-3}$ give $A_m=4A_{m-2}-A_{m-4}$ for $m\ge4$. With $a(n)=A_{2n}$ this is Theorem~\ref{thm:main}. The closed form follows from the roots $2\pm\sqrt3$ of $x^2-4x+1$ and the values $a(0),a(1)$, and the limit of the ratio from $|2-\sqrt3|<1$. \end{proof}

\section{Proof B: an order bound and a finite check}
\begin{proof}[Proof by the transfer matrix]
A profile $s\in\{0,\ldots,7\}$ records cells already occupied by dominoes entering the current column. Bit $r$ corresponds to row $r+1$, counting from the top. The outgoing mask $t$ records horizontal dominoes started in that column. Incoming and outgoing masks must be disjoint; the remaining cells must be empty or be one adjacent pair filled by a vertical domino. Thus $T_{s,t}=1$ exactly when
\[
s\mathbin{\&}t=0,\qquad 7\mathbin{\oplus}(s\mathbin{|}t)\in\{0,3,6\},
\]
where the symbols denote bitwise AND, XOR, and OR. Otherwise $T_{s,t}=0$.
With rows and columns ordered $0,1,\ldots,7$, this gives
\[
T=\begin{pmatrix}
0&1&0&0&1&0&0&1\\
1&0&0&0&0&0&1&0\\
0&0&0&0&0&1&0&0\\
0&0&0&0&1&0&0&0\\
1&0&0&1&0&0&0&0\\
0&0&1&0&0&0&0&0\\
0&1&0&0&0&0&0&0\\
1&0&0&0&0&0&0&0
\end{pmatrix}.
\]
The matrix is symmetric. Starting and ending in profile zero forbids dominoes crossing either outer boundary, so a product of its entries counts each tiling exactly once. For example, $(T^2)_{00}=3$, the three tilings of the $3\times2$ board.

The number of tilings of $3\times m$ is $(T^m)_{00}$ for the $8\times8$ column-profile matrix $T$, so $a(n)=(T^{2n})_{00}$ is annihilated by a monic polynomial $P(E)$ of degree at most 8 in the shift $E$ (Cayley--Hamilton for $T^2$). Let $Q(E)=E^2-4E+1$ and $d=Q(E)a$. Polynomials in $E$ commute, so $P(E)d=Q(E)P(E)a=0$: the difference $d$ obeys the same monic recurrence of order $\le8$, and a sequence like that vanishes once its first 8 terms do. Eight consecutive equations, $a(0),\dots,a(9)$, hold; hence $d\equiv0$. This proof does not use Proof~A and is the template implemented by \texttt{check\_recurrence} with \texttt{order\_bound=8}.

\end{proof}

\section{Confidence record}
\begin{table}[!ht]\centering\small
\caption{Evidence supporting the conclusions.}
\begin{tabular}{@{}p{6.2cm}p{4.2cm}p{3.6cm}@{}}\toprule
Statement & Evidence & Level\\\midrule
$a(n)$ for $n\le@@THREE@@$ & backtracking, transfer matrix, recurrences agree & checked to $n=@@THREE@@$, three methods\\
$a(n)$ for $n\le@@TWO@@$ & transfer matrix and recurrences agree & checked to $n=@@TWO@@$, two methods\\
$a(n)=4a(n-1)-a(n-2)$ for all $n$ & Proof A; Proof B; held-out terms; exhaustive to $n=60$ & proved (two independent proofs)\\
closed form and growth rate & algebra from the recurrence & proved\\
no polynomial formula & degree $\le8$ search; exponential growth & proved by growth\\
novelty & OEIS A001835 lists the sequence & not claimed\\\bottomrule\end{tabular}
\end{table}

\FloatBarrier
\section{Generating function and comparison of the proofs}
The recurrence gives a concise description as a formal power series. Put
$F(x)=\sum_{n\ge0}a(n)x^n$. Multiplying the recurrence by $x^n$ and
summing for $n\ge2$ yields
\[
(1-4x+x^2)F(x)=a(0)+(a(1)-4a(0))x=1-x,
\qquad F(x)=\frac{1-x}{1-4x+x^2}.
\]
The two roots of the denominator recover the closed form in Theorem~\ref{thm:main}. No convergence assumption is needed for this formal-series identity.

Proof~A uses two geometrically meaningful board families and explains the coefficient 4 by eliminating the corner-defect count. Proof~B uses eight boundary profiles and makes the finite verification sufficient through a justified recurrence-order bound. The bound 8 is sufficient, not minimal; the actual order is 2. Agreement of numerical implementations is useful for finding errors, but the all-size conclusion rests on these structural arguments, not on the length of the numerical search.

\section{Scope and reproducibility}
This note is an exposition of a classical enumeration, not a claim of an original research contribution. The local cases, transition matrix, and finite-check argument can be examined independently. The archived checks document the specified finite ranges; no proof assistant verifies the entire manuscript or its runtime.

\paragraph{Reproduce.} From the repository root, run
\begin{quote}\small\ttfamily
uv run --locked python demos/domino-research/reproduce/explore.py
\end{quote}
This recomputes the numbers; \texttt{build\_note.py} typesets this note from the archived record.
\begin{thebibliography}{1}
\bibitem{OEIS} OEIS Foundation Inc., \emph{The On-Line Encyclopedia of Integer Sequences}, entry A001835, \href{https://oeis.org/A001835}{oeis.org/A001835}, accessed October 9, 2026.
\end{thebibliography}
\end{document}
'''
three_max, two_max = verification_ranges(R)
TEX = TEX.replace('@@COUNT_SUMMARY@@', count_summary(R)).replace('@@THREE@@', str(three_max)).replace('@@TWO@@', str(two_max))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, default=HERE / 'paper')
    parser.add_argument('--compiler', help='Path to Tectonic 0.17.0')
    args = parser.parse_args()
    out = args.output_directory.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'paper.tex').write_text(TEX)
    check_layout(TEX, 'research')
    compile_in_place(out / 'paper.tex', 'research', compiler=args.compiler)
    shutil.copyfile(out / 'paper.pdf', HERE.parent / 'deliverables/paper.pdf')
    print('built deliverables/paper.pdf; comparison ranges:', three_max, two_max)
