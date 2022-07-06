import json
import requests
from datetime import datetime

MAX_APARTS_AT_FLOOR = 10  # заведомо большое (нереальное) количество квартир на этаже в подъезде
DEVIATION = 15  # 15 м2 - допустимое отклонение площади этажей из предположения, что квартиры с < 15 м2 маловероятны


def parsing_ids():
    """Парсит обзорную информацию для дома по заданному адресу"""
    with open("parsing_parameters.json", "r", encoding="utf-8") as file:
        parameters = json.load(file)
    headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/86.0.4240.111 Safari/537.36'}
    # urllib3.disable_warnings()
    response = requests.get(url="https://rosreestr.gov.ru/fir_rest/api/fir/address/fir_objects",
                            params=parameters, headers=headers, verify=False)
    response.raise_for_status()
    all_ids = response.json()

    with open("all_ids.json", "w", encoding='utf-8') as file:
        json.dump(all_ids, file, ensure_ascii=False, indent=4)


def parsing_details():
    """Парсит детальную информацию для объектов (не только квартиры, а все объекты с id)"""
    # Парсинг всего списка или пакетами по 50 запросов с паузой между пакетами 4-5 минут:
    # срабатывает или тот или другой способ, но больше похоже на нестабильность работы сайта росреестра,
    # чем на лимиты для одного ip. При обоих способах может потребоваться перезапуск парсинга при неудаче.
    # Ночью стабильнее. В крайнем случае можно парсить пакетами и сохранять результат в промежуточный файл,
    # с последующим объединением успешно спарсенных пакетов.
    with open("all_ids.json", "r", encoding="utf-8") as file:
        all_ids = json.load(file)
    list_ids = [item["objectId"] for item in all_ids if len(item["objectId"]) > 12]
    details = []
    for i in range(len(list_ids)):
        headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/86.0.4240.111 Safari/537.36'}
        response = requests.get(
            url="https://rosreestr.gov.ru/fir_rest/api/fir/fir_object/%s" % list_ids[i],
            headers=headers, verify=False)
        response.raise_for_status()
        _ = response.json()
        details.append(_)
        # Если парсить пакетами по 50 запросов:
        # if i % 50 == 0 and i != 0:
        #     time.sleep(random.randint(240, 300))

    with open("raw_details.json", "w", encoding='utf-8') as file:
        json.dump(details, file, ensure_ascii=False, indent=4)


def create_final_detail():
    """Из спарсенных объектов выбирает те, которые в адресе имеют указание, что это квартира, отсеивает квартиры
    с удаленными данными (иначе будут дубли - актуальные и удаленные записи для одного и того же объекта) и назначает
    квартирам ограниченный набор атрибутов (из большого набора исходных атрибутов)."""
    with open('raw_details.json', 'r') as file:
        raw_details = json.load(file)

    final_details = []
    for item in raw_details:
        try:
            object_name = item.get("objectData").get("objectName", "")
            if " кв" in item["objectData"]["addressNote"] and item["objectData"]["removed"] != 1 \
                    and "комната" not in object_name.lower() and "комнаты" not in object_name.lower(): # фильтр "комната/комнаты" отсекает записи о раздельной собственности на комнаты в многокомнатной квартире
                detail = {
                    "objectId": item["objectId"],
                    "addressNote": item.get("objectData").get("addressNote"),
                    "apartment": item.get("objectData").get("objectAddress").get("apartment"),
                    "areaValue": item.get("premisesData").get("areaValue"),
                    "premisesFloor": item.get("premisesData").get("premisesFloor"),
                }
                final_details.append(detail)
        except:
            pass
    # Для квартир с пустыми "premisesFloor" попробовать извлечь номер этажа из поля "objectName" в "raw_details.json"
    for item in final_details:
        if item["premisesFloor"] is None:
            for element in raw_details:
                if element["objectId"] == item["objectId"]:
                    if element.get("objectData").get("objectName"):
                        floor = element.get("objectData").get("objectName")[-4:].strip(". :аж")
                        if floor.isdigit():
                            item["premisesFloor"] = int(floor)
                        else:
                            item["premisesFloor"] = ""

    with open("final_details.json", "w", encoding='utf-8') as file:
        json.dump(final_details, file, ensure_ascii=False, indent=4)


def create_final_detail_sorted():
    """Унифицирует строковые значения для поля "apartment" с учетом литерных (типа "10а") и сдвоенных (типа "315, 316")
    номеров квартир и сортирует квартиры по этим унифицированным значениям"""
    with open("final_details.json", "r") as file:
        final_details_to_sort = json.load(file)

    for item in final_details_to_sort:
        num_to_sort = item["apartment"]
        if num_to_sort.isdigit():  # Проверить, что в номере квартиры только цифры
            while len(num_to_sort) < 4:
                num_to_sort = "0" + num_to_sort  # Дополнить номера до "0001", "0012", "0221"
        elif "," in num_to_sort:  # Разделить номера сдвоеных квартир типа "315, 316" и дополнить до вида "0315x"
            num = num_to_sort.split(",")
            num = num[0]
            while len(num) < 4:
                num = "0" + num
            num_to_sort = num + "x"
        elif " " in num_to_sort and "," not in num_to_sort: # Разделить номера квартир типа "414 к.1" и дополнить до вида "0414x"
            num = num_to_sort.split(",")
            num = num[0]
            while len(num) < 4:
                num = "0" + num
            num_to_sort = num + "x"
        else:  # Дополнить литерные номера квартир до вида "0001а"
            while len(num_to_sort) < 5:
                num_to_sort = "0" + num_to_sort
        item["num_to_sort"] = num_to_sort  # Добавить служебное поле "num_to_sort" для сортировки по нему
        item["data_calculated"] = 0  # Добавить ко всем объектам служебное поле "data_calculated" для различения
        # исходных данных и измененных в результате вычислений

    # Отсортировать квартиры по "num_to_sort":
    final_details_sorted = sorted(final_details_to_sort, key=lambda x: x["num_to_sort"])
    with open("final_details_sorted.json", "w", encoding="utf-8") as file:
        json.dump(final_details_sorted, file, ensure_ascii=False, indent=4)


def check_fullness():
    """Восстанавливает квартиры, отсутствующие в результатах парсинга. Вычисляет и проверяет непротиворечивость номеров
     этажей для квартир по условию возрастания серий этажей, равенству суммарной площади квартир на соседних этажах."""
    # Лист отсортированных данных по квартирам:
    with open("final_details_sorted.json", "r") as file:
        sorted_aparts = json.load(file)

    # Лист исходных спарсенных данных по квартирам:
    with open("raw_details.json", "r") as file:
        raw_details = json.load(file)

    # Лист унифицированных номеров квартир из sorted_aparts:
    aparts_list = [item["num_to_sort"] for item in sorted_aparts]

    # Преобразовать унифицированные номера квартир в числовые значения:
    apart_numbers = []
    for item in aparts_list:
        num = item.lstrip('0')
        num = num.rstrip('aаx')  # Одна "а" - латиница, другая - кириллица
        apart_numbers.append(int(num))

    # Наибольший и наименьший номер квартиры в доме:
    max_apart_numbers = max(apart_numbers)
    min_apart_numbers = min(apart_numbers)

    # Вычислить недостающие / пропущенные номера квартир в доме:
    # # Список недостающих номеров квартир:
    missing_numbers = []
    for apart in range(min_apart_numbers, max_apart_numbers + 1):
        if apart not in apart_numbers:
            missing_numbers.append(apart)
    missing_numbers = [str(item) for item in missing_numbers]

    # # Список унифицированных недостающих номеров квартир:
    list_num_to_sort = []
    for item in missing_numbers:
        num_to_sort = str(item)
        while len(num_to_sort) < 4:
            num_to_sort = '0' + num_to_sort
        list_num_to_sort.append(num_to_sort)

    # # Удалить расчетный пропущеный номер квартиры, если он является частью сдвоенной квартиры (num_to_sort с "х" на конце)
    for item in list_num_to_sort:
        apart = int(item.lstrip("0"))
        previous_apart = str(apart - 1)
        while len(previous_apart) < 4:
            previous_apart = "0" + previous_apart
        previous_apart = previous_apart + "x"
        for i in range(len(sorted_aparts)):
            if previous_apart == sorted_aparts[i]["num_to_sort"]:
                list_num_to_sort.remove(item)

    # Добавить недостающие квартиры в общий список с пустыми полями:
    # # Найти данные по пропущеным номерам в "raw_details.json" и добавить их в записи для недостающих квартир
    for item in list_num_to_sort:
        apart = item.lstrip("0")
        missing_apart = {
            "objectId": time_stamp(),
            "addressNote": "",
            "apartment": apart,
            "areaValue": 0,
            "premisesFloor": "",
            "num_to_sort": item,
            "data_calculated": 1,
        }
        sorted_aparts.append(missing_apart)
        for i in range(len(raw_details)):
            try:
                if raw_details[i].get("objectData").get("objectAddress").get("apartment") == apart:
                    if raw_details[i]["objectData"]["removed"] != 1:
                        sorted_aparts.remove(missing_apart)
                        missing_apart = {
                            "objectId": raw_details[i].get("objectId", time_stamp()),
                            "addressNote": raw_details[i].get("objectData").get("objectAddress").get("addressNotes", ""),
                            "apartment": apart,
                            "areaValue": raw_details[i].get("premisesData").get("areaValue", 0),
                            "premisesFloor": raw_details[i].get("premisesData").get("premisesFloor", ""),
                            "num_to_sort": item,
                            "data_calculated": 1,
                        }
                        sorted_aparts.append(missing_apart)
            except:
                pass
    # Отсортировать после добавления записей для недостающих квартир:
    all_apartments_restored = sorted(sorted_aparts, key=lambda x: x["num_to_sort"])

    # Восстановить отсутствующие номера этажей по значениям для этажей у предшествующей и следующей квартир.
    # Если квартира находится между квартирами на разных этажах, значению этажа присвоить среднее между этажами
    # для последующего уточнения. Если квартира может быть в разных подъездах (или последняя в предыдущем подъезде
    # или первая в следующем), установить значение этажа = 1000 для последующего уточнения. Значение 1000,
    # чтобы не ломать алгоритм разбивки на подъезды, и заведомо нереальное, чтобы можно было обработать и уточнить

    # # Список num_to_sort с отсутствующим номером этажа:
    missing_floors = []
    for item in all_apartments_restored:
        if item["premisesFloor"] == "":
            missing_floors.append(item["num_to_sort"])

    # # Лист уникальных значений этажей в доме:
    floors_list = [item["premisesFloor"] for item in all_apartments_restored if item["premisesFloor"] != ""]
    floors_list = sorted(list(set(floors_list)))

    # # Рассчитать значения для отсутствующих "premisesFloor" (работает при условии, что нет двух квартир подряд
    # # с пустыми значениями для "premisesFloor")
    if missing_floors:
        for item in missing_floors:
            for i in range(1, len(all_apartments_restored) - 1):
                current_apart = all_apartments_restored[i]
                previous_apart = all_apartments_restored[i - 1]
                next_apart = all_apartments_restored[i + 1]
                if current_apart["num_to_sort"] == item:
                    if previous_apart["premisesFloor"] == next_apart["premisesFloor"]:
                        current_apart["premisesFloor"] = previous_apart["premisesFloor"]
                    elif previous_apart["premisesFloor"] == next_apart["premisesFloor"] - 1:
                        current_apart["premisesFloor"] = previous_apart["premisesFloor"] + 0.5
                    else:
                        current_apart["premisesFloor"] = 1000
                    current_apart["data_calculated"] = 1

    # Исправить возможные ошибки в спарсенных значениях этажей, когда номер этажа текущей квартиры не совпадает
    # с номером этажей предшествующей и следующей квартирой, которые обе имеют одинаковый номер этажа:
    for i in range(1, len(all_apartments_restored) - 1):
        current_apart = all_apartments_restored[i]
        previous_apart = all_apartments_restored[i - 1]
        next_apart = all_apartments_restored[i + 1]
        if previous_apart["premisesFloor"] == next_apart["premisesFloor"] + 1 \
                and current_apart["premisesFloor"] != previous_apart["premisesFloor"]:
            current_apart["premisesFloor"] = previous_apart["premisesFloor"]
            current_apart["data_calculated"] = 1

    # Попробовать скорректировать вычисленные значения этажей типа 8.5 (квартиры на границах этажей)
    # # Лист значений этажей после корректировок:
    floors_list_2 = [item["premisesFloor"] for item in all_apartments_restored]
    floors_list_2 = sorted(list(set(floors_list_2)))  # В отличие от floors_list может содержать этажи типа 8.5 и 1000

    # # Лист некорректных значений этажей (как этажи, которые есть в floors_list_2 и которых нет в floors_list)
    wrong_floors = list(set(floors_list_2).difference(set(floors_list)))

    # # Список индексов в all_apartments_restored квартир с некорректными значениями этажей
    apart_indexes = []
    for item in wrong_floors:
        for i in range(len(all_apartments_restored)):
            if all_apartments_restored[i]["premisesFloor"] == item:
                apart_indexes.append(i)

    # # Скорректировать значения этажей для квартир из apart_indexes из условия равенства площади соседних этажей:
    for item in apart_indexes:
        if all_apartments_restored[item]["premisesFloor"] != 1000:  # Обработка для этажей со значениями 3.5, 6.5 и т.д.
            previous_floor = all_apartments_restored[item - 1]["premisesFloor"]
            next_floor = previous_floor + 1
            all_apartments_restored[item]["premisesFloor"] = previous_floor
            if all_apartments_restored[item]["areaValue"] == 0:
                j = 1
                number_at_previous = 1  # Счетчики количества квартир для previous_floor и next_floor
                number_at_next = 0
                while j < MAX_APARTS_AT_FLOOR:
                    if all_apartments_restored[item - j]["premisesFloor"] == previous_floor:
                        number_at_previous += 1
                    if all_apartments_restored[item + j]["premisesFloor"] == next_floor:
                        number_at_next += 1
                    j += 1
                previous_area = 0  # Расчет площади этажей при данной конфигурации квартир на этажах
                next_area = 0
                if number_at_previous == number_at_next:
                    for k in range(item - number_at_previous + 1, item + 1):
                        previous_area += all_apartments_restored[k]["areaValue"]
                    for n in range(item + 1, item + number_at_next + 1):
                        next_area += all_apartments_restored[n]["areaValue"]
                    if abs(next_area - previous_area) > DEVIATION:
                        all_apartments_restored[item]["areaValue"] = int(next_area - previous_area)
                elif number_at_previous - number_at_next == 2:
                    all_apartments_restored[item]["premisesFloor"] = next_floor
                    for k in range(item - number_at_previous + 1, item):
                        previous_area += all_apartments_restored[k]["areaValue"]
                    for n in range(item, item + number_at_next + 2):
                        next_area += all_apartments_restored[n]["areaValue"]
                    if abs(next_area - previous_area) > DEVIATION:
                        all_apartments_restored[item]["areaValue"] = int(abs(next_area - previous_area))
            else:
                j = 1
                previous_area = all_apartments_restored[item][
                    "areaValue"]  # Прибавляем площадь симметрично вверх и вниз по индексу
                next_area = all_apartments_restored[item + 1]["areaValue"]
                while j < MAX_APARTS_AT_FLOOR:
                    if all_apartments_restored[item - j]["premisesFloor"] == previous_floor:
                        previous_area += all_apartments_restored[item - j]["areaValue"]
                    if all_apartments_restored[item + j + 1]["premisesFloor"] == next_floor:
                        next_area += all_apartments_restored[item + j + 1]["areaValue"]
                    j += 1
                if abs(previous_area - next_area) < DEVIATION:
                    pass  # То есть назначение all_apartments_restored[item]["premisesFloor"] = previous_floor верно.
                else:  # Переносим квартиру на следующий этаж.
                    all_apartments_restored[item]["premisesFloor"] = next_floor
        else:  # Обработка для этажей со значениями 1000
            previous_floor = all_apartments_restored[item - 1]["premisesFloor"]
            pre_previous_floor = previous_floor - 1
            all_apartments_restored[item]["premisesFloor"] = previous_floor
            j = 0
            start1 = item
            start2 = item
            previous_area = 0
            pre_previous_area = 0
            while j < MAX_APARTS_AT_FLOOR * 2:
                j += 1
                if all_apartments_restored[item - j]["premisesFloor"] == previous_floor:
                    start1 += -1
                    start2 += -1
                if all_apartments_restored[item - j]["premisesFloor"] == pre_previous_floor:
                    start2 += -1
                if all_apartments_restored[item - j]["premisesFloor"] == pre_previous_floor - 1:
                    break
            for k in range(start1, item + 1):
                previous_area += all_apartments_restored[k]["areaValue"]
            for n in range(start2, start1):
                pre_previous_area += all_apartments_restored[n]["areaValue"]
            if abs(previous_area - pre_previous_area) < DEVIATION:
                pass  # То есть назначение all_apartments_restored[item]["premisesFloor"] = previous_floor верно.
            else:  # Переносим квартиру в следующий подъезд на нижний этаж. Верно, если не попались квартиры с площадью 0.
                all_apartments_restored[item]["premisesFloor"] = all_apartments_restored[item + 1]["premisesFloor"]

    with open('all_apartments_restored.json', 'w', encoding='utf-8') as file:
        json.dump(all_apartments_restored, file, ensure_ascii=False, indent=4)


def floors_average_area(entrance):
    """Вычисляет среднее значение площади квартир на этажах в подъезде. Принимает список
    данных для всех квартир в подъезде. Возвращает среднее значение площади этажей."""
    # Какие номера этажей есть в подъезде, список уникальных номеров этажей:
    floors_set_as_list = list(set([item["premisesFloor"] for item in entrance]))
    floors_set_as_list = floors_set_as_list[1:-1] # Исключить первый и последний этажи (часто особые случаи для них)
    # Список площадей этажей из floors_set_as_list:
    floors_area_list = []
    for i in range(len(floors_set_as_list)):
        floor_area = 0
        for j in range(len(entrance)):
            if entrance[j]["premisesFloor"] == floors_set_as_list[i]:
                floor_area += entrance[j]["areaValue"]
        floor_area = round(floor_area)
        floors_area_list.append(floor_area)
    # Среднее значение площади этажа в подъезде:
    average_area = int(sum(floors_area_list) / len(floors_area_list))
    return average_area


def check_wrong_floors(apartments_by_entrances):
    """Проверяет правильность распределения квартир по этажам в подъезде из условия, что площадь этажа
    должна быть равна средней площади этажей по подъезду (при допущении, что все этажи в подъезде имеют равную
    площадь, то есть подъезды с секциями этажей разной площади вне области определения данной функции).
    Принимает в качестве аргумента список квартир, распределенных по подъездам. Возвращает словарь с номерами подъездов
    и номерами ошибочных этажей в этих подъездах. Список этажей содержит как минимум два ошибочных этажа, так как
    предполагается, что отклонение связано с ошибочным распределением квартир между двумя соседними этажами.
    Этаж с номером 1 исключается из рассмотрения, так как первые этажи с другим количеством квартир на этаже
    и с другой суммарной площадью квартир - частый случай, а не ошибка."""
    wrong_floors_list = []
    for n in range(len(apartments_by_entrances)):
        entrance = apartments_by_entrances[n]  # Подъезд дома
        floors_set_as_list = list(set([item["premisesFloor"] for item in entrance]))  # Номера этажей в подъезде
        if floors_set_as_list[0] == 1: # Исключить этаж с номером 1
            floors_set_as_list = floors_set_as_list[1:]
        floors_area_list = []  # Лист для значений площадей этажей подъезда
        wrong_floors = []  # Лист для номеров этажей с отклоняющейся от средней площадью этажа
        for i in range(len(floors_set_as_list)):  # Вычисление площади этажей из floors_set_as_list
            floor_area = 0
            for j in range(len(entrance)):
                if entrance[j]["premisesFloor"] == floors_set_as_list[i]:
                    floor_area += entrance[j]["areaValue"]
            floor_area = round(floor_area)
            floors_area_list.append(floor_area)
        average_area = int(sum(floors_area_list) / len(floors_area_list))
        for i in range(len(floors_area_list)):
            if floors_area_list[i] > average_area + DEVIATION or floors_area_list[i] < average_area - DEVIATION:
                wrong_floors.append(floors_set_as_list[i])
        wf = {
            "entrance": n + 1,
            "wrongFloors": wrong_floors,
        }
        wrong_floors_list.append(wf)
    return wrong_floors_list


def create_entrances():
    """Распределяет квартиры по подъездам дома (назначает каждой квартире атрибут "entrance". Граница между подъездами
    определяется по квартире, чей этаж меньше этажа квартиры с предшествующим номером квартиры. """
    # Список всех данных по квартирам в доме:
    with open("all_apartments_restored.json", "r") as file:
        all_apartments = json.load(file)
    # Распределить квартиры по подъездам по индексам, на которых происходит переход с последнего этажа на меньший этаж
    # # Лист всех этажей для квартир из all_apartments:
    floors_list = [item["premisesFloor"] for item in all_apartments]
    # # Лист индексов для разбивки всех квартир на подъезды:
    separate_indexes = [0]
    for i in range(1, len(floors_list)):
        if floors_list[i] - floors_list[i - 1] < 0:
            separate_indexes.append(i)
    separate_indexes.append(len(floors_list))
    # # Назначить каждой квартире в доме подъезд, в котором она расположена:
    all_apartments_with_entrances = all_apartments[:]
    for i in range(1, len(separate_indexes)):
        for j in range(separate_indexes[i]):
            if all_apartments_with_entrances[j].get("entrance"):
                pass
            else:
                all_apartments_with_entrances[j]["entrance"] = i
    with open("all_apartments_with_entrances.json", "w", encoding="utf-8") as file:
        json.dump(all_apartments_with_entrances, file, ensure_ascii=False, indent=4)

    # # Разбить общий список квартир в доме на подъезды как вложенные списки типа: [[подъезд1], [подъезд2], [] []]
    all_apartments_by_entrances = []
    for i in range(1, len(separate_indexes)):
        start = separate_indexes[i - 1]
        stop = separate_indexes[i]
        entr = all_apartments_with_entrances[start:stop]
        all_apartments_by_entrances.append(entr)

    # Проверить наличие квартир с нулевой площадью и вычислить отсутствующие значения
    for i in range(len(all_apartments_by_entrances)):
        entrance = all_apartments_by_entrances[i]  # Подъезд
        null_area = []
        for item in entrance:
            if item["areaValue"] == 0:
                apart_id = item["objectId"]
                apart_floor = item["premisesFloor"]
                null_area.append([apart_id, apart_floor])
        average_area = floors_average_area(entrance)
        for item in null_area:
            floor = item[1]
            floor_area = 0
            for j in range(len(entrance)):
                if entrance[j]["premisesFloor"] == floor:
                    floor_area += entrance[j]["areaValue"]
            for k in range(len(entrance)):
                if entrance[k]["objectId"] == item[0] and average_area > floor_area:
                    floor_area += entrance[k]["areaValue"]
                    all_apartments_by_entrances[i][k]["areaValue"] = int(average_area - floor_area)


    # Проверить правильность распределения квартир по этажам в подъездах
    wrong_floors_list = check_wrong_floors(all_apartments_by_entrances)

    # # Перераспределить квартиры на ошибочных этажах
    for i in range(len(wrong_floors_list)):
        if wrong_floors_list[i]["wrongFloors"]:
            floors = wrong_floors_list[i]["wrongFloors"]  # Список ошибочных этажей в подъезде
            entrance = all_apartments_by_entrances[i]  # Подъезд
            average_area = floors_average_area(entrance)  # Средняя площадь этажа в подъезде
            aparts_at_floors = []  # Список всех aparts_at_floor
            for j in range(len(floors)):
                aparts_at_floor = []  # Список пар "id квартиры - площадь квартиры" на текущем этаже
                for item in entrance:
                    if item["premisesFloor"] == floors[j]:
                        id_and_area = [item["objectId"], item["areaValue"]]
                        aparts_at_floor.append(id_and_area)
                aparts_at_floors.append(aparts_at_floor)
            for j in range(len(floors) - 1):
                if floors[j] == floors[j + 1] - 1:  # Если этажи соседние, объединить в общий список
                    total_aparts = aparts_at_floors[j] + aparts_at_floors[j + 1]  # Все квартиры на обоих этажах
                    area = 0
                    for k in range(len(total_aparts)):  # По одной суммируем площадь квартир в total_aparts
                        area += total_aparts[k][1]
                        if average_area + DEVIATION > area > average_area - DEVIATION:  # Признак конца этажа
                            object_id = total_aparts[k][0]  # id квартиры, которой заканчивается этаж
                    for n in range(len(entrance)):  # Переназначить номер этажа, чтобы выровнять площади этажей
                        if entrance[n]["objectId"] == object_id:
                            if entrance[n]["premisesFloor"] == floors[j + 1]:  # Если квартире приписан следующий этаж
                                entrance[n]["premisesFloor"] = floors[j]  # то назначить ей текущий
                                entrance[n]["data_calculated"] = 1
                            elif entrance[n] == floors[j]:  # Если квартире приписан текущий этаж
                                entrance[n + 1]["premisesFloor"] = floors[
                                    j + 1]  # то следующей кв. назначить след. этаж
                                entrance[n + 1]["data_calculated"] = 1
            all_apartments_by_entrances[i] = entrance

    with open("all_apartments_by_entrances.json", "w", encoding="utf-8") as file:
        json.dump(all_apartments_by_entrances, file, ensure_ascii=False, indent=4)


def create_house_plan():
    """Создает план дома как состоящего из подъездов, в каждом подъезде - этажи с указанием номера этажа,
    его общей площади и списка квартир на этаже, где квартира представлена в виде пары "номер - площадь"."""
    with open("all_apartments_by_entrances.json", "r") as file:
        all_apartments_by_entrances = json.load(file)
    house_plan = []
    for i in range(len(all_apartments_by_entrances)):
        floors_in_entrance = list(set([item["premisesFloor"] for item in all_apartments_by_entrances[i]]))
        entrance_plan = []
        for item in floors_in_entrance:
            current_floor = []
            current_floor_area = 0
            for j in range(len(all_apartments_by_entrances[i])):
                if all_apartments_by_entrances[i][j]["premisesFloor"] == item:
                    _ = [all_apartments_by_entrances[i][j]["apartment"], all_apartments_by_entrances[i][j]["areaValue"]]
                    current_floor_area += all_apartments_by_entrances[i][j]["areaValue"]
                    current_floor.append(_)
            entrance_plan.append({"floor": item, "floor_area": round(current_floor_area),
                                  "apartments_num_and_area": current_floor})
        house_plan.append({"entrance": i + 1, "plan": entrance_plan})

    with open("house_plan.json", "w", encoding="utf-8") as file:
        json.dump(house_plan, file, ensure_ascii=False, indent=4)


def prepare_to_print(house_plan_file):
    """Формирует строки равной длины номеров квартир на этажах и с интервалом между подъездами для вывода на экран"""
    with open(house_plan_file, "r") as file:
        house_plan = json.load(file)

    floors_list = []  # Список всех номеров этажей в доме (может не совпадать со списком этажей в отдельном подъезде)
    for i in range(len(house_plan)):
        flr = house_plan[i]["plan"]
        floors = []
        for item in flr:
            floors.append(item["floor"])
        floors_list.extend(floors)
    floors_list = list(set(floors_list))
    max_floor = max(floors_list)

    # Список этажей с квартирами на них, внутри этажа квартиры разделены также и по подъездам
    aparts_by_floors = []
    for i in range(1, max_floor + 1):
        lst2 = []
        for j in range(len(house_plan)):
            lst1 = []
            for k in range(len(house_plan[j]["plan"])):
                if house_plan[j]["plan"][k]["floor"] == i:
                    for n in range(len(house_plan[j]["plan"][k]["apartments_num_and_area"])):
                        lst1.append(house_plan[j]["plan"][k]["apartments_num_and_area"][n][0])
            lst2.append(lst1)
            dct = {
                "floor": i,
                "aparts_at_the_floor": lst2,
            }
        aparts_by_floors.append(dct)

    # Сделать строковые значения номеров квартир одной длины за счет добавления пробелов и
    # выровнять по центру для симметрии при выводе на экран
    for item in aparts_by_floors:
        for i in range(len(house_plan)):  # len(house_plan) = количество подъездов
            a = item["aparts_at_the_floor"][i]
            b = [item.center(8) for item in a]
            item["aparts_at_the_floor"][i] = b

    # Сцепить номера квартир на этаже и по подъездам в одну строку и добавить символы "|" по краям и между номерами квартир
    for item in aparts_by_floors:
        for i in range(len(house_plan)):
            a = item["aparts_at_the_floor"][i]
            b = "|" + "|".join(a) + "|"
            item["aparts_at_the_floor"][i] = b

    # Определить максимальную длину сцепленной строки, чтобы строки меньшей длины расширить до максимальной для симметрии
    max_length = 0
    for item in aparts_by_floors:
        for i in range(len(house_plan)):
            if len(item["aparts_at_the_floor"][i]) > max_length:
                max_length = len(item["aparts_at_the_floor"][i])

    # Инвертировать порядок этажей, чтобы на экране этажи с меньшим номером отображались ниже этажей с большим номером
    aparts_by_floors.reverse()
    with open("aparts_by_floors.json", "w", encoding="utf-8") as file:
        json.dump(aparts_by_floors, file, ensure_ascii=False, indent=4)

    # Сформировать итоговые строки для вывода на экран
    strings_to_print = []
    for i in range(len(aparts_by_floors)):
        string_to_print = ""
        for j in range(len(house_plan)):
            a = aparts_by_floors[i]["aparts_at_the_floor"][j]
            if len(a) < max_length:
                a = a + " " * (max_length - len(a))
            a = a + " " * 10
            string_to_print += a
        strings_to_print.append(string_to_print)
    return strings_to_print


def time_stamp():
    now = datetime.utcnow()
    now = str(now.timestamp())
    moment = now.replace(".", "")
    return moment


def create_address():
    with open("parsing_parameters.json", "r", encoding="utf-8") as file:
        parameters = json.load(file)
    return parameters


def create_file_name_and_file(name):
    with open(name, "r", encoding="utf-8") as file:
        old_file = json.load(file)
    file_name = time_stamp()
    file_path = f"data/{file_name}.json"
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(old_file, file, ensure_ascii=False, indent=4)
    return file_path


def create_aparts_by_floors(house_plan_file):
    with open(house_plan_file, "r") as file:
        house_plan = json.load(file)

    floors_list = []  # Список всех номеров этажей в доме (может не совпадать со списком этажей в отдельном подъезде)
    for i in range(len(house_plan)):
        flr = house_plan[i]["plan"]
        floors = []
        for item in flr:
            floors.append(item["floor"])
        floors_list.extend(floors)
    floors_list = list(set(floors_list))
    max_floor = max(floors_list)

    # Список этажей с квартирами на них, внутри этажа квартиры разделены также и по подъездам
    aparts_by_floors = []
    for i in range(1, max_floor + 1):
        lst2 = []
        for j in range(len(house_plan)):
            lst1 = []
            for k in range(len(house_plan[j]["plan"])):
                if house_plan[j]["plan"][k]["floor"] == i:
                    for n in range(len(house_plan[j]["plan"][k]["apartments_num_and_area"])):
                        lst1.append(house_plan[j]["plan"][k]["apartments_num_and_area"][n][0])
            lst2.append(lst1)
            dct = {
                "floor": i,
                "aparts_at_the_floor": lst2,
            }
        aparts_by_floors.append(dct)

    # Сделать строковые значения номеров квартир одной длины за счет добавления пробелов и
    # выровнять по центру для симметрии при выводе на экран
    for item in aparts_by_floors:
        for i in range(len(house_plan)):  # len(house_plan) = количество подъездов
            a = item["aparts_at_the_floor"][i]
            b = [item.center(8) for item in a]
            item["aparts_at_the_floor"][i] = b

    # Сцепить номера квартир на этаже и по подъездам в одну строку и добавить символы "|" по краям и между номерами квартир
    for item in aparts_by_floors:
        for i in range(len(house_plan)):
            a = item["aparts_at_the_floor"][i]
            b = "|" + "|".join(a) + "|"
            item["aparts_at_the_floor"][i] = b

    # Определить максимальную длину сцепленной строки, чтобы строки меньшей длины расширить до максимальной для симметрии
    max_length = 0
    for item in aparts_by_floors:
        for i in range(len(house_plan)):
            if len(item["aparts_at_the_floor"][i]) > max_length:
                max_length = len(item["aparts_at_the_floor"][i])

    # Инвертировать порядок этажей, чтобы на экране этажи с меньшим номером отображались ниже этажей с большим номером
    aparts_by_floors.reverse()
    return aparts_by_floors


def correct_apartment():
    pass
