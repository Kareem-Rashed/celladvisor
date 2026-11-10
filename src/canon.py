from itertools import permutations

PERMS = list(permutations(range(4)))


def get_bit(number, position):
    return (number >> position) & 1


def set_bit(number, position):
    return number | (1 << position)


def row_to_pins(row):
    return [get_bit(row, pin) for pin in range(4)]


def pins_to_row(pins):
    row = 0
    for pin, value in enumerate(pins):
        if value:
            row = set_bit(row, pin)
    return row


def permute(tt, p):
    new_tt = 0
    for old_row in range(16):
        old_pins = row_to_pins(old_row)
        new_pins = [0, 0, 0, 0]
        for j in range(4):
            new_pins[j] = old_pins[p[j]]
        new_row = pins_to_row(new_pins)
        if get_bit(tt, old_row):
            new_tt = set_bit(new_tt, new_row)
    return new_tt


def negate_inputs(tt, mask):
    """
    negate inputs for the NPN function by xor'ing with a mask
    set bits in mask = invert
    """
    new_tt = 0

    for row in range(16):
        if get_bit(tt, row ^ mask):
            new_tt = set_bit(new_tt, row)

    return new_tt

def canon_p(tt):
    return min(permute(tt, p) for p in PERMS)


def canon_pn(tt):
    flipped = 0xFFFF - tt
    return min(canon_p(tt), canon_p(flipped))


def canon_npn(tt):
    return min(canon_pn(negate_inputs(tt, mask)) for mask in range(16))

def used_inputs(tt):
    used = set()
    for pin in range(4):
        for row in range(16):
            pins = row_to_pins(row)
            pins[pin] = 1 - pins[pin]
            other_row = pins_to_row(pins)
            if get_bit(tt, row) != get_bit(tt, other_row):
                used.add(pin)
    return used




