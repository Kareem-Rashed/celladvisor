"""
cost(tt) -> (transistors, single_stage)

Convention: tt is a 16-bit int, bit m is f(A,B,C,D) for the minterm m whose
bit 0 is input A, bit 1 is B, bit 2 is C, bit 3 is D.


One static CMOS stage computes Y = !g where g is a series-parallel (AND/OR)
formula of the inputs with no inverted literal. The pull-down network is g,
the pull-up network is its dual, so transistors = 2 * (literals in g).
Series depth: AND adds up in the pull-down, OR adds up in the pull-up.
Both must be <= MAX_SERIES (3).

single_stage == True  <=>  !f has such a formula within the depth limit.

Otherwise a rough multi-stage estimate:
  - choose a set S of inputs to invert (2 transistors each),
  - then either  f = !g  with g a positive AND/OR formula of !f (S flipped), or
    f = !(!f) with g a positive formula of f (S flipped) plus an output
    inverter (2 transistors),
  - each case costs 2 * literals(g) + 2 * |S| (+2) (rough estimate)
  - Functions needing an input in both polarities (XOR-like) get BIG (a fallback estimate)
"""
from functools import lru_cache
from itertools import combinations

MASK = 0xFFFF
MAX_SERIES = 3
VAR = [0xAAAA, 0xCCCC, 0xF0F0, 0xFF00]   # truth tables of A, B, C, D
BIG = 40 # fallback estimate (XOR-like)


def support(tt):
    """
    Indices of inputs the function really depends on
    """
    s = []
    for i in range(4):
        sh = 1 << i
        lo = tt & ~VAR[i] & MASK
        hi = (tt & VAR[i]) >> sh
        if lo != hi:
            s.append(i)
    return s


def flip(tt, i):
    """Truth table of f with input i complemented."""
    sh = 1 << i
    return (((tt & VAR[i]) >> sh) | ((tt & ~VAR[i] & MASK) << sh)) & MASK


@lru_cache(maxsize=None) #least recenty used
def _single_table():
    """
    tt -> min literals of a positive AND/OR formula with series depth <= 3
    """
    best = {}

    def add(tt, pd, pu, n):
        d = best.setdefault(tt, {})
        if d.get((pd, pu), 99) > n:
            d[(pd, pu)] = n
            return True
        return False

    for v in VAR:
        add(v, 1, 1, 1)
    changed = True
    while changed:
        changed = False
        items = [(t, pd, pu, n) for t, d in best.items() for (pd, pu), n in d.items()]
        for t1, pd1, pu1, n1 in items:
            for t2, pd2, pu2, n2 in items:
                if n1 + n2 > 12:
                    continue
                if pd1 + pd2 <= MAX_SERIES: # AND
                    changed |= add(t1 & t2, pd1 + pd2, max(pu1, pu2), n1 + n2)
                if pu1 + pu2 <= MAX_SERIES: # OR
                    changed |= add(t1 | t2, max(pd1, pd2), pu1 + pu2, n1 + n2)
    return {t: min(d.values()) for t, d in best.items()}


@lru_cache(maxsize=None)
def _positive_table():
    """
    tt -> min literals of a positive AND/OR formula, no depth limit
    """
    best = {v: 1 for v in VAR}
    changed = True
    while changed:
        changed = False
        items = list(best.items())
        for t1, n1 in items:
            for t2, n2 in items:
                for t in (t1 & t2, t1 | t2):
                    if best.get(t, 99) > n1 + n2:
                        best[t] = n1 + n2
                        changed = True
    return best


def cost(tt):
    """
    Return (transistors, single_stage) for a 16-bit truth table
    """
    tt &= MASK
    sup = support(tt)
    if not sup:
        return (0, False) # constant. no cell needed
    nf = ~tt & MASK
    single = _single_table()
    if nf in single: # f = !g, g positive, depth ok
        return (2 * single[nf], True)

    # rough multi-stage estimate 
    pos = _positive_table()
    est = []
    for k in range(len(sup) + 1):
        for S in combinations(sup, k):
            g1, g2 = nf, tt
            for i in S:
                g1, g2 = flip(g1, i), flip(g2, i)
            if g1 in pos: # f = !g1
                est.append(2 * pos[g1] + 2 * k)
            if g2 in pos: # f = inverter(!g2)
                est.append(2 * pos[g2] + 2 * k + 2)
    if est:
        return (min(est), False)
    return (BIG, False)