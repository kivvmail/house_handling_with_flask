from flask import Flask, render_template, redirect, request, flash, url_for
import json
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from wtforms import StringField, SubmitField, SelectField
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from regions import get_macroregion_id, make_list_macroregions, make_list_regions, get_region_id, get_macroregion_name,\
    get_region_name
from app_functions import parsing_ids, parsing_details, create_final_detail, create_final_detail_sorted, \
    check_fullness, create_entrances, create_house_plan, prepare_to_print, create_address, create_file_name_and_file,\
    create_aparts_by_floors


app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config["SECRET_KEY"] = "dfgrt"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///housesdata.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class House(db.Model):
    __tablename__ = "houses"
    id = db.Column(db.Integer, primary_key=True)
    macroregion_id = db.Column(db.String(30))
    macroregion_name = db.Column(db.String(100))
    region_id = db.Column(db.String(30))
    region_name = db.Column(db.String(100))
    street = db.Column(db.String(60))
    house = db.Column(db.String(10))
    building = db.Column(db.String(10))
    details_file = db.Column(db.String(60))
    aparts_by_entrances_file = db.Column(db.String(60))
    house_plan_file = db.Column(db.String(60))
    house_plan_latest_file = db.Column(db.String(60))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    address = db.Column(db.String(280))


class MacroRegionForm(FlaskForm):
    macroregion = SelectField('Выберите область / край / республику из списка и нажмите "Продолжить":',
                              choices=make_list_macroregions(),
                              validate_choice=True, validators=[DataRequired()], default="Select Macroregion")
    submit = SubmitField("Продолжить")


class Address(FlaskForm):
    street = StringField("Улица: ", validators=[DataRequired()])
    house_number = StringField("Номер дома, в том числе с литерой (вида 12а): ", validators=[DataRequired()])
    building_number = StringField("Номер корпуса, если есть: ")
    submit = SubmitField("Продолжить")


class FormParsing(FlaskForm):
    submit = SubmitField("Парсить")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/new-house", methods=["GET", "POST"])
def new_house():
    global macroregion
    form_macro_region = MacroRegionForm()
    if request.method == "POST":
        if form_macro_region.validate_on_submit():
            if form_macro_region.macroregion.data == "Select Macroregion":
                flash("Не выбран макрорегион")
                return redirect("new-house")
            else:
                macroregion = form_macro_region.macroregion.data
                return redirect("select-region")
    return render_template("new-house.html", form_macro_region=form_macro_region)


@app.route("/select-region", methods=["GET", "POST"])
def select_region():
    global macroregion, region
    macroregion_id = get_macroregion_id(macroregion)
    list_regions = make_list_regions(macroregion_id)

    class RegionForm(FlaskForm):
        region = SelectField("Выберите регион:", choices=list_regions,
                             validate_choice=True, validators=[DataRequired()], default="Select Region")
        submit = SubmitField("Продолжить")

    form_region = RegionForm()
    if request.method == "POST":
        if form_region.validate_on_submit():
            if form_region.region.data == "Select Region":
                flash("Не выбран регион")
                return redirect("select-region")
            else:
                region = form_region.region.data
                return redirect("set-address")
    return render_template("select-region.html", form_region=form_region, macroregion=macroregion)


@app.route("/set-address", methods=["GET", "POST"])
def set_address():
    global macroregion, region, success_parsing_base
    form_address = Address()
    macroregion_id = get_macroregion_id(macroregion)
    region_id = get_region_id(macroregion, region)
    if request.method == "POST":
        if form_address.validate_on_submit():
            street = form_address.street.data
            house = form_address.house_number.data
            building = form_address.building_number.data
            parsing_parameters = {
                "macroRegionId": macroregion_id,
                "regionId": region_id,
                "street": street,
                "house": house,
                "building": building,
                "apartment": "*",
            }
            macroregion_name = macroregion
            region_name = region
            address = f"{macroregion_name} {region_name} {parsing_parameters['street']} " \
                      f"{parsing_parameters['house']} {parsing_parameters['building']}"
            houses = House.query.all()
            list_addresses = []
            for item in houses:
                list_addresses.append(item.address)
            if address in list_addresses:
                message = "Дом с таким адресом уже есть в списке обработанных домов"
                flash(message)
                return redirect("all-houses")
            else:
                with open("parsing_parameters.json", "w", encoding="utf-8") as file:
                    json.dump(parsing_parameters, file, ensure_ascii=False, indent=4)
                return redirect("overview-parsing")
    return render_template("set-address.html", form_address=form_address, macroregion=macroregion, region=region)


@app.route("/overview-parsing", methods=["GET", "POST"])
def overview_parsing():
    form_parsing = FormParsing()
    if request.method == "POST":
        if form_parsing.validate_on_submit():
            try:
                parsing_ids()
                return redirect("details-parsing")
            except:
                message = 'Неудачная попытка установления связи с сайтом Росреестр, пожалуйста, ' \
                          'нажмите кнопку "Парсить" еще раз через некоторое время.'
                flash(message)
                return redirect("overview-parsing")
    return render_template("overview-parsing.html", form_parsing=form_parsing)


@app.route("/details-parsing", methods=["GET", "POST"])
def details_parsing():
    form_parsing = FormParsing()
    if request.method == "POST":
        if form_parsing.validate_on_submit():
            try:
                parsing_details()
                return redirect("results")
            except:
                message = 'Неудачная попытка установления связи с сайтом Росреестр, пожалуйста, ' \
                          'нажмите кнопку "Парсить" еще раз через некоторое время.'
                flash(message)
                return redirect("details-parsing")
    return render_template("details-parsing.html", form_parsing=form_parsing)


@app.route("/results", methods=["GET", "POST"])
def results():
    create_final_detail()
    create_final_detail_sorted()
    check_fullness()
    create_entrances()
    create_house_plan()
    strings_to_print = prepare_to_print("house_plan.json")
    with open("aparts_by_floors.json", "r") as file:
        aparts_by_floors = json.load(file)

    parameters = create_address()
    house_plan_file = create_file_name_and_file("house_plan.json")
    details_file = create_file_name_and_file("final_details.json")
    aparts_by_entrances_file = create_file_name_and_file("all_apartments_by_entrances.json")
    house_plan_latest_file = create_file_name_and_file("house_plan.json")
    macroregion_name = get_macroregion_name(parameters["macroRegionId"])
    region_name = get_region_name(parameters["macroRegionId"], parameters["regionId"])
    address = f"{macroregion_name} {region_name} {parameters['street']} {parameters['house']} {parameters['building']}"
    db_entry = House(macroregion_id=parameters["macroRegionId"], region_id=parameters["regionId"],
                     street=parameters["street"], house=parameters["house"], building=parameters["building"],
                     details_file=details_file, aparts_by_entrances_file=aparts_by_entrances_file,
                     house_plan_file=house_plan_file, house_plan_latest_file=house_plan_latest_file,
                     macroregion_name=macroregion_name, region_name=region_name, address=address)
    db.session.add(db_entry)
    db.session.commit()
    floors_list = []
    for i in range(len(strings_to_print)):
        floor_number = str(aparts_by_floors[i]['floor'])
        if len(floor_number) < 2:
            floor_number = " " + floor_number
        floor = f"Floor {floor_number}          " + strings_to_print[i]
        floors_list.append(floor)
    return render_template("results.html", floors_list=floors_list)


@app.route("/all-houses", methods=["GET", "POST"])
def all_houses():
    houses = db.session.query(House).all()
    return render_template("all-houses.html", houses=houses)


@app.route("/plans/<id>", methods=["GET", "POST"])
def house_plan_latest_file(id):
    house = House.query.filter_by(id=id).first()
    latest_file = house.house_plan_latest_file
    strings_to_print = prepare_to_print(latest_file)
    aparts_by_floors = create_aparts_by_floors(latest_file)
    floors_list = []
    for i in range(len(strings_to_print)):
        floor_number = str(aparts_by_floors[i]['floor'])
        if len(floor_number) < 2:
            floor_number = " " + floor_number
        floor = f"Floor {floor_number}          " + strings_to_print[i]
        floors_list.append(floor)
    return render_template("plans.html", floors_list=floors_list, house=house)


if __name__ == "__main__":
    app.run(debug=True)
