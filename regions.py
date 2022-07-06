import requests
import json

MACRO_REG = [{"id": 102000000000, "name": "Ямало-Ненецкий АО"}, {"id": 103000000000, "name": "Краснодарский край"},
             {"id": 101000000000, "name": "Алтайский край"}, {"id": 104000000000, "name": "Красноярский край"},
             {"id": 107000000000, "name": "Ставропольский край"}, {"id": 105000000000, "name": "Приморский край"},
             {"id": 114000000000, "name": "Белгородская область"}, {"id": 115000000000, "name": "Брянская область"},
             {"id": 108000000000, "name": "Хабаровский край"}, {"id": 112000000000, "name": "Астраханская область"},
             {"id": 111000000000, "name": "Архангельская область"}, {"id": 111100000000, "name": "Ненецкий АО"},
             {"id": 110000000000, "name": "Амурская область"}, {"id": 119000000000, "name": "Вологодская область"},
             {"id": 118000000000, "name": "Волгоградская область"},
             {"id": 117000000000, "name": "Владимирская область"},
             {"id": 122000000000, "name": "Нижегородская область"},
             {"id": 120000000000, "name": "Воронежская область"}, {"id": 125000000000, "name": "Иркутская область"},
             {"id": 126000000000, "name": "Республика Ингушетия"},
             {"id": 127000000000, "name": "Калининградская область"},
             {"id": 124000000000, "name": "Ивановская область"}, {"id": 128000000000, "name": "Тверская область"},
             {"id": 133000000000, "name": "Кировская область"}, {"id": 132000000000, "name": "Кемеровская область"},
             {"id": 130000000000, "name": "Камчатский край"}, {"id": 129000000000, "name": "Калужская область"},
             {"id": 136000000000, "name": "Самарская область"}, {"id": 134000000000, "name": "Костромская область"},
             {"id": 142000000000, "name": "Липецкая область"}, {"id": 141000000000, "name": "Ленинградская область"},
             {"id": 138000000000, "name": "Курская область"}, {"id": 140000000000, "name": "Санкт-Петербург"},
             {"id": 147000000000, "name": "Мурманская область"}, {"id": 137000000000, "name": "Курганская область"},
             {"id": 149000000000, "name": "Новгородская область"}, {"id": 145000000000, "name": "Москва"},
             {"id": 144000000000, "name": "Магаданская область"}, {"id": 146000000000, "name": "Московская область"},
             {"id": 153000000000, "name": "Оренбургская область"}, {"id": 152000000000, "name": "Омская область"},
             {"id": 154000000000, "name": "Орловская область"}, {"id": 150000000000, "name": "Новосибирская область"},
             {"id": 157000000000, "name": "Пермский край"}, {"id": 158000000000, "name": "Псковская область"},
             {"id": 156000000000, "name": "Пензенская область"}, {"id": 160000000000, "name": "Ростовская область"},
             {"id": 163000000000, "name": "Саратовская область"}, {"id": 165000000000, "name": "Свердловская область"},
             {"id": 164000000000, "name": "Сахалинская область"}, {"id": 161000000000, "name": "Рязанская область"},
             {"id": 168000000000, "name": "Тамбовская область"}, {"id": 170000000000, "name": "Тульская область"},
             {"id": 169000000000, "name": "Томская область"}, {"id": 166000000000, "name": "Смоленская область"},
             {"id": 173000000000, "name": "Ульяновская область"}, {"id": 176000000000, "name": "Забайкальский край"},
             {"id": 175000000000, "name": "Челябинская область"}, {"id": 171000000000, "name": "Тюменская область"},
             {"id": 171100000000, "name": "Ханты-Мансийский АО"}, {"id": 179000000000, "name": "Республика Адыгея"},
             {"id": 180000000000, "name": "Республика Башкортостан"}, {"id": 177000000000, "name": "Чукотский АО"},
             {"id": 178000000000, "name": "Ярославская область"}, {"id": 184000000000, "name": "Республика Алтай"},
             {"id": 185000000000, "name": "Республика Калмыкия"}, {"id": 188000000000, "name": "Республика Марий Эл"},
             {"id": 183000000000, "name": "Кабардино-Балкарская Республика"},
             {"id": 187000000000, "name": "Республика Коми"}, {"id": 186000000000, "name": "Республика Карелия"},
             {"id": 181000000000, "name": "Республика Бурятия"}, {"id": 182000000000, "name": "Республика Дагестан"},
             {"id": 193000000000, "name": "Республика Тыва"}, {"id": 194000000000, "name": "Удмуртская Республика"},
             {"id": 192000000000, "name": "Республика Татарстан"},
             {"id": 190000000000, "name": "Республика Северная Осетия"},
             {"id": 191000000000, "name": "Карачаево-Черкесская Республика"},
             {"id": 198000000000, "name": "Республика Саха (Якутия)"},
             {"id": 196000000000, "name": "Чеченская Республика"},
             {"id": 197000000000, "name": "Чувашская Республика"}, {"id": 195000000000, "name": "Республика Хакасия"},
             {"id": 189000000000, "name": "Республика Мордовия"}, {"id": 199000000000, "name": "Еврейская А.обл."},
             {"id": 39100000000000, "name": "Республика Крым"}, {"id": 39200000000000, "name": "Севастополь"}]


def get_macroregion_id(macroregion):
    for item in MACRO_REG:
        if item["name"] == macroregion:
            macroregion_id = item["id"]
            return macroregion_id


def get_macroregion_name(macroregion_id):
    for item in MACRO_REG:
        if item["id"] == macroregion_id:
            macroregion_name = item["name"]
            return macroregion_name


def get_region_name(macroregion_id, region_id):
    dict_regions = make_dict_regions(macroregion_id)
    for item in dict_regions:
        if item["id"] == region_id:
            region_name = item["name"]
    return region_name


def get_region_id(macroregion, region):
    macroregion_id = get_macroregion_id(macroregion)
    dict_regions = make_dict_regions(macroregion_id)
    for item in dict_regions:
        if item["name"] == region:
            region_id = item["id"]
            return region_id


def get_settlement_id(region_id, settlement):
    url_settlement = f"http://rosreestr.ru/api/online/regions/{region_id}"
    headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/86.0.4240.111 Safari/537.36'}
    response = requests.get(url_settlement, headers=headers, verify=False)
    response.raise_for_status()
    list_settlements = response.json()
    for item in list_settlements:
        if item["name"] == settlement:
            settlement_id = item["id"]
            return settlement_id


def get_list_settlements(macroregion, region):
    region_id = get_region_id(macroregion, region)
    url_settlement = f"http://rosreestr.ru/api/online/regions/{region_id}"
    headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/86.0.4240.111 Safari/537.36'}
    response = requests.get(url_settlement, headers=headers, verify=False)
    response.raise_for_status()
    list_settlements = response.json()
    list_settlements_names = [item["name"] for item in list_settlements]
    list_settlements_names.append("Select Settlement")
    list_settlements_names.sort()
    return list_settlements_names


def make_list_macroregions():
    list_macroregions = []
    for item in MACRO_REG:
        list_macroregions.append(item["name"])
    list_macroregions.append("Select Macroregion")
    list_macroregions.sort()
    return list_macroregions


def make_list_regions(macroregion_id):
    with open("regions_database.json", "r", encoding="utf-8") as file:
        regions = json.load(file)
    for item in regions:
        if item["macroregion_id"] == macroregion_id:
            dict_regions = item["regions"]
            list_regions = [item["name"] for item in dict_regions]
            list_regions.append("Select Region")
            list_regions.sort()
            return list_regions


def make_dict_regions(macroregion_id):
    with open("regions_database.json", "r", encoding="utf-8") as file:
        regions = json.load(file)
    for item in regions:
        if item["macroregion_id"] == macroregion_id:
            dict_regions = item["regions"]
            return dict_regions
