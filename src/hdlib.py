import re, sys, csv
from itertools import product

TOKEN = re.compile(r"[A-Za-z_]\w*|[01]|[!&|^()*+']")

def tokenize(expr):
    toks = TOKEN.findall(expr)
    if "".join(toks) != re.sub(r"\s+", "", expr):
        raise ValueError(f"unparsed characters in function: {expr!r}")
    return toks

def support(expr):
    return sorted({t for t in tokenize(expr) if t[0].isalpha() or t[0] == "_"})

def eval_function(expr, order):
    """Truth table as an int: bit i = output when input order[k] = bit k of i."""
    n = len(order)
    rows = 1 << n
    mask = (1 << rows) - 1

    env = {name: sum(1 << i for i in range(rows) if (i >> k) & 1)
           for k, name in enumerate(order)}
    toks = tokenize(expr)
    pos = 0
    
    def peek():
        return toks[pos] if pos < len(toks) else None

    def eat():
        nonlocal pos
        t = toks[pos]
        pos += 1
        return t

    def p_or():
        v = p_xor()
        while peek() in ("|", "+"):
            eat()
            v |= p_xor()
        return v

    def p_xor():
        v = p_and()
        while peek() == "^":
            eat()
            v ^= p_and()
        return v

    def p_and():
        v = p_not()
        while peek() in ("&", "*"):
            eat()
            v &= p_not()
        return v

    def p_not():
        if peek() == "!":
            eat()
            return mask ^ p_not()
        v = p_atom()
        while peek() == "'":
            eat()
            v = mask ^ v
        return v

    def p_atom():
        t = eat()
        if t == "(":
            v = p_or()
            assert eat() == ")"
            return v
        if t in ("0", "1"):
            return mask if t == "1" else 0
        return env[t]

    v = p_or()
    if pos != len(toks):
        raise ValueError(f"trailing tokens in {expr!r}")
    return v

def pad_to_4(tt, n):
    """Extend an n-input table (n<=4) to 16 bits by tiling
    unused inputs are don't-care."""
    bits = 1 << n
    return sum(((tt >> (i & (bits - 1))) & 1) << i for i in range(16))

def _block_end(text, start):
    """Index just past the brace block whose '{' is at or after start."""
    i = text.index("{", start)
    depth = 0
    while True:
        c = text[i]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return i + 1
        i += 1

def read_cells(path):
    """Yield (name, [(pin, function), ...], flags) for each cell."""
    text = re.sub(r"/\*.*?\*/", "", open(path).read(), flags=re.S)
    for m in re.finditer(r'\bcell\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', text):
        body = text[m.end() - 1:_block_end(text, m.end() - 1)]
        outs = []
        for pm in re.finditer(r'\bpin\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', body):
            pbody = body[pm.end() - 1:_block_end(body, pm.end() - 1)]
            fm = re.search(r'\bfunction\s*:\s*"([^"]+)"', pbody)
            if re.search(r'direction\s*:\s*"output"', pbody) and fm:
                outs.append((pm.group(1), fm.group(1)))
        seq = bool(re.search(r'\b(ff|latch|statetable)\s*\(', body))
        tri = "three_state" in body
        yield m.group(1), outs, seq or tri

def build_table(lib_path, canon_p, canon_pn):
    rows, wide, skipped = [], [], []
    for name, outs, nonlogic in read_cells(lib_path):
        if nonlogic or len(outs) != 1:
            skipped.append(name); continue
        expr = outs[0][1]; order = support(expr); n = len(order)
        tt = eval_function(expr, order)
        if n <= 4:
            tt16 = pad_to_4(tt, n)
            rows.append((name, n, f"{tt16:04x}",
                         f"{canon_p(tt16):04x}", f"{canon_pn(tt16):04x}"))
        else:
            wide.append((name, n, order, tt))
    return rows, wide, skipped

if __name__ == "__main__":
    import os
    from canon import canon_p, canon_pn
    rows, wide, skipped = build_table(sys.argv[1], canon_p, canon_pn)
    os.makedirs(os.path.dirname(sys.argv[2]) or ".", exist_ok=True)
    with open(sys.argv[2], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cell", "n_inputs", "tt_hex", "class_p", "class_pn"])
        w.writerows(rows)
    print(f"{len(rows)} cells, {len({r[3] for r in rows})} P classes, "
          f"{len({r[4] for r in rows})} PN classes, "
          f"{len(wide)} wide (>4 inputs), {len(skipped)} skipped")
    print("skipped:", " ".join(skipped))