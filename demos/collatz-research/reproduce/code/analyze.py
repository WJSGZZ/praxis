"""Regenerate presentation decimals from the exact, already verified certificate."""
import json
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    certificate = json.loads((ROOT/'runs/certificate.json').read_text())
    rows = certificate['envelope_rows']
    with localcontext() as ctx:
        ctx.prec = 60
        limit = 1/(6*Decimal(2).ln())
        normalized = []
        for q in (5,17,29,41,147,306,646):
            row = next(r for r in rows if r['q'] == q)
            value = Decimal(row['maximum_offset'])/(Decimal(row['A'])*q)
            normalized.append(dict(q=q, k=row['k'], M_over_Aq=str(value),
                                   limit=str(limit), difference=str(value-limit)))
        row = max(rows, key=lambda r:r['exception_floor'])
        k, q = row['k'], row['q']
        unconstrained = (1 << (k-q))*(3**q-2**q)
        record = dict(k=k, q=q, H=row['exception_floor'],
                      unconstrained_bound=unconstrained//(row['D']-row['A']),
                      unconstrained_to_constrained_offset_ratio=str(Decimal(unconstrained)/row['maximum_offset']))
    output = dict(normalized_offsets=normalized, record=record,
                  numerical_scope='Decimal60 for display/asymptotic illustration; all certification uses integer arithmetic')
    (ROOT/'runs/analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    print('Presentation analysis regenerated; certificate unchanged.')


if __name__ == '__main__':
    main()
