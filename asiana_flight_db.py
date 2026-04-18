# Asiana Airlines Flight Number to Route Mapping (Sample)
# Format: { "FlightNo": ("DepAirport", "ArrAirport") }

FLIGHT_ROUTES = {
    # Long Haul
    "202": ("ICN", "LAX"), "201": ("LAX", "ICN"),
    "204": ("ICN", "LAX"), "203": ("LAX", "ICN"),
    "212": ("ICN", "SFO"), "211": ("SFO", "ICN"),
    "222": ("ICN", "JFK"), "221": ("JFK", "ICN"),
    "272": ("ICN", "SEA"), "271": ("SEA", "ICN"),
    "232": ("ICN", "HNL"), "231": ("HNL", "ICN"),
    "501": ("ICN", "CDG"), "502": ("CDG", "ICN"),
    "521": ("ICN", "LHR"), "522": ("LHR", "ICN"),
    "541": ("ICN", "FRA"), "542": ("FRA", "ICN"),
    "551": ("ICN", "IST"), "552": ("IST", "ICN"),
    "561": ("ICN", "FCO"), "562": ("FCO", "ICN"),
    "601": ("ICN", "SYD"), "602": ("SYD", "ICN"),
    
    # Regional / Short Haul
    "711": ("ICN", "NRT"), "712": ("NRT", "ICN"),
    "102": ("ICN", "NRT"), "101": ("NRT", "ICN"),
    "112": ("ICN", "KIX"), "111": ("KIX", "ICN"),
    "114": ("ICN", "KIX"), "113": ("KIX", "ICN"),
    "132": ("ICN", "FUK"), "131": ("FUK", "ICN"),
    "134": ("ICN", "FUK"), "133": ("FUK", "ICN"),
    "311": ("ICN", "PEK"), "312": ("PEK", "ICN"),
    "331": ("ICN", "PEK"), "332": ("PEK", "ICN"),
    "361": ("ICN", "PVG"), "362": ("PVG", "ICN"),
    "367": ("ICN", "PVG"), "368": ("PVG", "ICN"),
    "701": ("ICN", "MNL"), "702": ("MNL", "ICN"),
    "703": ("ICN", "MNL"), "704": ("MNL", "ICN"),
    "731": ("ICN", "SGN"), "732": ("SGN", "ICN"),
    "735": ("ICN", "SGN"), "736": ("SGN", "ICN"),
    "751": ("ICN", "BKK"), "752": ("BKK", "ICN"),
    "741": ("ICN", "BKK"), "742": ("BKK", "ICN"),
    "717": ("ICN", "TPE"), "718": ("TPE", "ICN"),
    "711": ("ICN", "TPE"), "712": ("TPE", "ICN"), # Dup check
    "172": ("ICN", "OKA"), "171": ("OKA", "ICN"),
    "152": ("ICN", "CTS"), "151": ("CTS", "ICN"),
}

def get_route(flight_no):
    # Strip "OZ" or spaces
    f_clean = "".join(filter(str.isdigit, str(flight_no)))
    return FLIGHT_ROUTES.get(f_clean, (None, None))
