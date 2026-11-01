from aig_reader import lit_to_var


def remove_dominated(cut_list):
    kept = []
    for cut in cut_list:
        dominated = False
        for other in cut_list:
            if (other < cut):
                dominated = True
        if not dominated:
            kept.append(cut)

    return kept
#since we have at most 4 inputs, O(n^2) is fine

def combine(left_cuts, right_cuts):
    combined = []
    for x in left_cuts:
        for y in right_cuts:
            # make union
             u = x | y
             if len(u) <= 4 and u not in combined:
                 combined.append(u)
    return combined


def enumerate_cuts(sources, ands):
    cuts = {}

    cuts[0] = [frozenset()]

    for s in sources:  
        cuts[s] = [frozenset([s])]

    for g in sorted(ands):
        #get the two input literals of gate g
        lit0, lit1 = ands[g]

        left = lit_to_var(lit0)
        right = lit_to_var(lit1)

        new_cuts = [frozenset([g])] + combine(cuts[left], cuts[right])

        cuts[g] = remove_dominated(new_cuts)

    return cuts


