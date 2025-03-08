#airtime_calculator.py
import math

def calculate_airtime(payload_size, sf, bw, cr=1, preamble=8):
    tsym = (2 ** sf) / bw
    t_preamble = (preamble + 4.25) * tsym
    DE = 1 if (sf >= 11 and bw == 125000) else 0
    payload_symb = 8 + max(math.ceil((8 * payload_size - 4 * sf + 28 + 16) / (4 * (sf - 2 * DE))) * (cr + 4), 0)
    airtime = t_preamble + payload_symb * tsym
    return airtime

