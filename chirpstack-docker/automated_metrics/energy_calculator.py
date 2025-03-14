VOLTAGE = 3.3   # Volts
CURRENT = 0.03  # 30 mA

def calculate_energy(airtime):
    """
    Estimate energy used for a single uplink transmission.
    :param airtime: float, in seconds
    :return: float, in Joules (V * I * t)
    """
    return VOLTAGE * CURRENT * airtime
