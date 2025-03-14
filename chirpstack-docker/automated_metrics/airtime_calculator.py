import math

def calculate_airtime(payload_size, sf, bw, cr=1, preamble=8):
    """
    Calculate LoRa airtime based on LoRaWAN parameters.
    :param payload_size: int, in bytes
    :param sf: spreading factor (7..12)
    :param bw: bandwidth in Hz (default 125000)
    :param cr: coding rate (CR_4_5 => 1)
    :param preamble: typically 8 for LoRaWAN
    :return: airtime in seconds (float)
    """
    tsym = (2 ** sf) / bw
    t_preamble = (preamble + 4.25) * tsym
    # Low data rate optimization
    DE = 1 if (sf >= 11 and bw == 125000) else 0
    # Header enabled => IH = 0
    IH = 0

    # Calculate payload symbols
    numerator = (8 * payload_size) - (4 * sf) + 28 + 16 - (20 * IH)
    denominator = 4 * (sf - 2 * DE)
    payload_symb_nb = 8 + max(
        math.ceil(numerator / denominator) * (cr + 4),
        0
    )

    airtime = t_preamble + (payload_symb_nb * tsym)
    return airtime
