from aig_reader import read_aag, lit_to_var, is_inverted


def _simulate(ands, root, leaf_values):
    """Value of node `root` given {leaf_var: 0/1}. Raises ValueError if the
    cone reaches a source that is not a leaf (so it isn't a valid cut)."""
    memo = dict(leaf_values)
    memo.setdefault(0, 0)  # the constant node

    def val(var):
        if var in memo:
            return memo[var]
        if var not in ands:
            raise ValueError(f"node {var} is outside the cut")
        a, b = ands[var]
        va = val(lit_to_var(a)) ^ is_inverted(a)
        vb = val(lit_to_var(b)) ^ is_inverted(b)
        memo[var] = va & vb
        return memo[var]

    return val(root)


def cut_truth_table(ands, root, leaves):
    """16-bit truth table of a cut; leaves[k] is input k (A = bit 0).
    Fewer than 4 leaves works: unused inputs are never read."""
    assert len(leaves) <= 4
    tt = 0
    for row in range(16):
        values = {leaf: (row >> k) & 1 for k, leaf in enumerate(leaves)}
        tt |= _simulate(ands, root, values) << row
    return tt


def verify_cut(aig_path, root, leaves, tt):
    """True if tt is the function of `root` over `leaves` (leaves[k] = input k)."""
    _, ands = read_aag(open(aig_path).read())
    try:
        return cut_truth_table(ands, root, list(leaves)) == tt
    except ValueError:
        return False