import inflect


def round_to_dp(f, dp):
    if (dp <= 0):
        return round (f)
    factor = pow(10, dp)
    return round (f * factor) / factor


fraction_lookup = { .25: 'a quarter', .5: 'a half', .75: 'three quarters' }
def constant_fractions(decimal: float):
    return fraction_lookup.get(decimal, None)


# Normalise duration to years in words.
def normalise_duration(duration: str | None, unit: str | None, decimal_places = 5):
    # Unit is 'Year(s)', 'Month(s)', and 'Week(s)'.
    if (duration is None or unit is None):
        return None
    
    normalised = float(duration)
    match unit:
        case 'Week(s)':
            normalised /= float(52)
        case 'Month(s)':
            normalised /= float(12)
        case _:
            pass
    
    normalised = round_to_dp(normalised, decimal_places)

    engine = inflect.engine()
    mod1 = normalised % 1
    normalised_int = int(normalised)

    # Return int-value of number if in floating-point format.
    #   E.g.,'two' if normalised == 2.0, instead of 'two point zero'.
    normalised_string = engine.number_to_words(normalised_int if (mod1 == 0) else normalised)

    # Return word as a base-quarter fraction, if applicable.
    known_fraction = constant_fractions(mod1)
    if (known_fraction):
        if (normalised_int != 0):
            normalised_string = F"{engine.number_to_words(normalised_int)} and {known_fraction}"

    return normalised_string


if (__name__ == '__main__'):
    print ('Years')
    print (normalise_duration('5.5', 'Year(s)'))
    print (normalise_duration('.5', 'Year(s)'))
    print (normalise_duration('.25', 'Year(s)'))
    print (normalise_duration('.75', 'Year(s)'))
    print (normalise_duration('83.5', 'Year(s)'))
    print (normalise_duration('2.25', 'Year(s)'))
    print (normalise_duration('4.75', 'Year(s)'))
    print (normalise_duration('2', 'Year(s)'))

    print ('Months')
    print (normalise_duration('18', 'Month(s)'))
    print (normalise_duration('6', 'Month(s)'))
    print (normalise_duration('3', 'Month(s)'))
    print (normalise_duration('9', 'Month(s)'))
    print (normalise_duration('21', 'Month(s)'))
    print (normalise_duration('30', 'Month(s)'))
    print (normalise_duration('27', 'Month(s)'))
    print (normalise_duration('33', 'Month(s)'))
    print (normalise_duration('24', 'Month(s)'))
    print (normalise_duration('5.236', 'Month(s)'))
    print (normalise_duration('534.444', 'Month(s)'))

    print ('Weeks')
    print (normalise_duration('26', 'Week(s)'))
    print (normalise_duration('78', 'Week(s)'))
    print (normalise_duration('52', 'Week(s)'))
    print (normalise_duration('104', 'Week(s)'))
    print (normalise_duration('128.43882', 'Week(s)'))

#
# Master of BA Original - C81FF38C-FC61-4A2A-B5F5-3BCFAE11120A
# Master of BA New      - AA4467F1-D9ED-486B-AF74-7860110031E0
# ROWID='C81FF38C-FC61-4A2A-B5F5-3BCFAE11120A' or ROWID='AA4467F1-D9ED-486B-AF74-7860110031E0'
#
# RMCAD Original - F6B9E2CC-C042-44FD-AEC7-77CC58F24C4B
# RMCAD New      - 56D9B0CC-B575-45AB-B3CC-BF624671B501
# ROWID='F6B9E2CC-C042-44FD-AEC7-77CC58F24C4B' or ROWID='56D9B0CC-B575-45AB-B3CC-BF624671B501'
#
# BE(Hons) Original - F32E2E4E-3224-4D9D-9AA0-1D154792A56D
# BE(Hons) New      - 23D354A2-2D50-4B04-BF64-FEF847A32C16
# ROWID='F32E2E4E-3224-4D9D-9AA0-1D154792A56D' or ROWID='23D354A2-2D50-4B04-BF64-FEF847A32C16'