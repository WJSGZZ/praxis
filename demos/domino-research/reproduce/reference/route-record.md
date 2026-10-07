# 路线记录：Count domino tilings of a 3 x 2n rectangle（exploratory）

## 发现的结构
- **transfer**（derived）：the count is u^T M^n v for an 8x8 integer matrix M (column profiles)
- **local**（derived）：the leftmost column splits the rectangle into smaller ones: A_m = A_{m-2} + 2 B_{m-1}, B_m = A_{m-1} + B_{m-2}

## 候选路线
### guess：guess a linear recurrence from data, test on held-out terms  〔exploring〕
- 假设：order_bound（derived；若不成立：enlarge the bound until it is justified）
- 攻击〔survived〕：the recurrence continues to hold；方法：4 held-out terms, exhaustive check to n = 60, finite-check proof

### polynomial：guess a polynomial formula in n  〔killed〕
- 结论：growth is exponential (ratio -> 2 + sqrt(3)); no polynomial of degree <= 8 fits

### split：prove it from the column decomposition  〔chosen〕
- 依据的结构：local
- 攻击〔survived〕：the case analysis is exhaustive；方法：compare A_m, B_m with backtracking counts for small boards
- 结论：a direct proof, cross-checked by the finite check

## 保留的中间结果
- **order_bound_result**（proved_finite_check）：finite check on 10 consecutive terms proves a(n)=4a(n-1)-a(n-2) for all n
