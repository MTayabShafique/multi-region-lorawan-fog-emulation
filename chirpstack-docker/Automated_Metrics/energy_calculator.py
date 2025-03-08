#energy_calculator.py
VOLTAGE = 3.3
CURRENT = 0.03  # 30 mA

def calculate_energy(airtime):
    return VOLTAGE * CURRENT * airtime
