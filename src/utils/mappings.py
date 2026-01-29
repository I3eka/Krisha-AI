"""
Mappings for Krisha.kz API IDs.
Derived from api_references/region/getAllregions/getAllregions.json
and api_references/category/getSearchList/getSearchList_response.json
"""

REGION_MAP = {
    "Kazakhstan": "1",
    "Almaty": "2",
    "Astana": "105",
    "Shymkent": "278",
    "Abay Region": "3729",
    "Semey": "222",
    "Akmola Region": "112",
    "Kokshetau": "119",
    "Kosshy": "731",
    "Aktobe Region": "124",
    "Aktobe": "125",
    "Almaty Region": "132",
    "Konaev": "168",
    "Kaskelen": "172",
    "Talgar": "194",
    "Atyrau Region": "213",
    "Atyrau": "214",
    "Kulsary": "215",
    "East Kazakhstan Region": "216",
    "Ust-Kamenogorsk": "224",
    "Ridder": "221",
    "Altay": "219",
    "Zhambyl Region": "227",
    "Taraz": "230",
    "Zhetysu Region": "3731",
    "Taldykorgan": "195",
    "West Kazakhstan Region": "232",
    "Uralsk": "234",
    "Aksay": "233",
    "Karaganda Region": "235",
    "Karaganda": "239",
    "Temirtau": "245",
    "Balkhash": "237",
    "Kostanay Region": "247",
    "Kostanay": "250",
    "Rudny": "252",
    "Kyzylorda Region": "253",
    "Kyzylorda": "256",
    "Baikonur": "885",
    "Mangystau Region": "257",
    "Aktau": "258",
    "Zhanaozen": "259",
    "Pavlodar Region": "260",
    "Pavlodar": "262",
    "Ekibastuz": "263",
    "North Kazakhstan Region": "264",
    "Petropavlovsk": "267",
    "Turkestan Region": "270",
    "Turkestan": "276",
    "Kentau": "273",
    "Arys": "271",
    "Ulytau Region": "3727",
    "Zhezkazgan": "238",
    "Satpayev": "244",
}

CATEGORY_MAP = {
    "Buy Apartment": "1",
    "Buy House/Dacha": "62",
    "Rent Apartment (Monthly)": "2",
    "Rent Apartment (Daily)": "57",
    "Rent Apartment (Hourly)": "58",
    "Rent House/Dacha (Monthly)": "65",
    "Rent House/Dacha (Daily)": "66",
    "Rent Room": "9",
}


def get_region_id_by_name(name: str) -> str:
    """
    Helper to find region ID case-insensitively.
    Defaults to Kazakhstan (1) if not found.
    """
    if not name:
        return "1"

    name_lower = name.lower().strip()
    for key, val in REGION_MAP.items():
        if key.lower() == name_lower:
            return val

    return "1"
