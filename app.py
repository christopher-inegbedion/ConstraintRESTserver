from constraints.constraint_main.constraint import Constraint
from flask import Flask, request
import jsonpickle
from stage.stage import Stage, StageGroup
from task_pipeline.pipeline import Pipeline
from task_main.task import Task
from user import create_new_user
from constraint_models.create_constraint_util import CreateConstraintUtil
import json
from werkzeug.serving import WSGIRequestHandler
WSGIRequestHandler.protocol_version = "HTTP/1.1"

app = Flask(__name__)

all_users = {}
all_tasks = {}
all_stage_groups = {}

all_constraint_views = {}


@app.route('/')
def index():
    return f"all users: {all_users}, all tasks: {all_tasks}"


@app.route("/constraints")
def get_all_constraints():
    constraints = []
    for constraint in CreateConstraintUtil.all_constraints:
        constraint_obj = CreateConstraintUtil.all_constraints[constraint]
        number_of_inputs_required = constraint_obj.model.input_count
        is_constraint_required = number_of_inputs_required != 0
        constraints.append(
            {
                "constraint_name": constraint_obj.name,
                "constraint_desc": constraint_obj.description,
                "model": constraint_obj.model.name,
                "is_configuration_input_required": constraint_obj.model.configuration_input_required,
                "configuration_input_amount": constraint_obj.model.configuration_input_count,
                "configuration_params": constraint_obj.model.config_parameters,
                "required": is_constraint_required,
                "for_payment": constraint_obj.model.for_payment

            }
        )

    return {"constraints": constraints}


@app.route("/constraint_view/<constraint_name>", methods=["GET", "POST"])
def constraint_view(constraint_name):
    global all_constraint_views

    if request.method == "GET":
        if constraint_name in all_constraint_views:
            return {
                "result": "success",
                "constraint": constraint_name,
                "view": all_constraint_views[constraint_name]
            }
        else:
            return {
                "result": "fail"
            }
    elif request.method == "POST":
        try:
            constraint_view = jsonpickle.decode(request.form["view"])
            all_constraint_views[constraint_name] = constraint_view

            return {"result": "success"}
        except:
            return {"result": "fail"}


@app.route("/create/<name>")
def create_user(name):
    user = create_new_user(name)
    all_users[name] = user
    return json.dumps(all_users[name].__dict__)


@app.route("/user/<name>")
def get_user(name):
    if name in all_users:
        user = json.dumps(all_users[name].__dict__)
        return user
    else:
        return "fail"


@app.route("/create_task", methods=["POST", "GET"])
def create_task():
    global all_stage_groups

    task_name = request.form["task_name"]
    task_desc = request.form["task_desc"]
    properties = jsonpickle.decode(request.form["properties"])

    price = request.form["price"]
    currency = request.form["currency"]
    price_constraint_name = request.form["price_constraint_name"]
    price_constraint = CreateConstraintUtil.create_constraint(
        price_constraint_name)
    price_constraint_stage = request.form["price_constraint_stage"]

    task_stage_group_id = request.form["stage_group_id"]
    stage_group: StageGroup = all_stage_groups[task_stage_group_id]
    stage_group._get_stage_with_name(
        price_constraint_stage).add_constraint(price_constraint)

    task: Task = Task(task_name, task_desc)
    task.set_price(price)
    task.set_currency(currency)
    task.set_price_constraint(price_constraint)
    task.price_constraint_stage = price_constraint_stage
    if (properties != None):
        for property in properties:
            i = properties[property]
            task.add_property(
                i["name"], i["value"], i["selected_denom"])
    task.set_constraint_stage_config(stage_group)
    all_tasks[str(task.id)] = task
    print(task.__dict__)

    print(f"task properties: {task.get_selected_properties()}")

    return json.dumps({"task_id": str(task.id)})


@app.route("/task")
def get_all_tasks():
    global all_tasks

    all_task_id = []
    for id in all_tasks:
        all_task_id.append(id)
    return {"tasks": all_task_id}


@app.route("/task/<id>")
def get_task(id):
    global all_tasks
    try:
        if id in all_tasks:
            task: Task = all_tasks[id]
            stages = []

            if task.constraint_stage_config != None:
                if len(task.constraint_stage_config.stages) > 0:
                    for stage in task.constraint_stage_config.stages:
                        stages.append(stage.name)
            data = {
                "msg": "success",
                "id": str(task.id),
                "name": task.name,
                "desc": task.description,
                "date_created": task.date_created,
                "price": task.price,
                "currency": task.currency,
                "price_constraint_name": task.price_constraint.name,
                "price_constraint_stage": task.price_constraint_stage,
                "stage_group_id": str(task.constraint_stage_config.id),
                "task_properties": task.get_selected_properties(),

            }
            return json.dumps(data)
        else:
            return {
                "msg": "not_found"
            }
    except:
        return {
            "msg": "server error"
        }


@app.route("/task/property/")
def get_all_properties():
    try:
        all_properties = {"properties": Task.get_available_properties()}
        return all_properties
    except:
        return {
            "msg": "server error"
        }


@app.route("/task/currency/")
def get_all_currencies():
    try:
        all_currencies = {"currencies": Task.currencies}
        return all_currencies
    except:
        return {
            "msg": "server error"
        }


@app.route("/task/property/<property_name>/denomination")
def get_property_denominations(property_name):
    return {
        "denominations": Task.get_property_denominations(property_name)
    }


@app.route("/stage_group", methods=["GET", "POST"])
def get_stage_groups():
    global all_stage_groups

    if request.method == "GET":
        return f"all stage groups: {all_stage_groups}"
    elif request.method == "POST":
        stages_data = json.loads(request.data)["stages"]
        # print(json.loads(request.data))
        stage_group = StageGroup()
        for stage in stages_data:
            stage_name = stage["stage_name"]
            constraints = stage["constraints"]
            new_stage = Stage(stage_name)
            for constraint in constraints:
                constraint_name = constraint["constraint_name"]
                config_inputs = constraint["config_inputs"]
                if constraint_name in CreateConstraintUtil.all_constraints:
                    constraint_obj: Constraint = CreateConstraintUtil.create_constraint(
                        constraint_name)
                    if constraint_obj.model.configuration_input_required:
                        for input in config_inputs["config_inputs"]:
                            constraint_obj.add_configuration_input(
                                input)
                    new_stage.add_constraint(constraint_obj)
                else:
                    return {"result": "fail", "msg": f"constraint {constraint_name} not found"}

            stage_group.add_stage(new_stage)
        all_stage_groups[str(stage_group.id)] = stage_group

    return {
        "result": "success",
        "msg": str(stage_group.id)
    }


@app.route("/stage_group/<stage_group_id>", methods=["GET", "POST"])
def get_stage_group(stage_group_id):
    global all_stage_groups
    if request.method == "GET":
        if stage_group_id in all_stage_groups:
            stage_group: StageGroup = all_stage_groups[stage_group_id]
            stages = []
            for stage in stage_group.stages:
                constraints = []
                for constraint in stage.constraints:
                    constraints.append(constraint.name)
                stages.append({
                    "stage_name": stage.name,
                    "constraints": constraints
                })

            return {
                "result": "success",
                "stage_group_id": stage_group.id,
                "stages": stages
            }
        else:
            return {"result": "fail"}
    elif request.method == "POST":
        pass


@app.route("/task/<task_id>/stage_group/<stage_group_id>/<stage_name>", methods=["GET", "POST"])
def stage_details(task_id, stage_group_id, stage_name):
    global all_stage_groups
    if request.method == "GET":
        if stage_group_id in all_stage_groups:
            stage_group: StageGroup = all_stage_groups[stage_group_id]
            for stage in stage_group.stages:
                if stage.name == stage_name:
                    constraints = []
                    for constraint in stage.constraints:
                        is_constraint_required = constraint.model.input_count != 0
                        task: Task = all_tasks[task_id]
                        constraints.append({
                            "constraint_name": constraint.name,
                            "constraint_desc": constraint.description,
                            "config_inputs": constraint.configuration_inputs,
                            "required": is_constraint_required,
                        })

                    return {
                        "stage_name": stage_name,
                        "constraints": constraints
                    }
    elif request.method == "POST":
        constraint_name = request.form["constraint_name"]
        if constraint_name in CreateConstraintUtil.all_constraints:
            pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
