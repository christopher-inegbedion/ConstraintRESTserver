from constraint_models.delivery1_model import DeliveryModel
from constraint_models.chat_model import ChatModel
from constraint_models.time_range_model import TimeRangeModel
from constraint_models.password_model import PasswordModel
from constraint_models.product_link_model import ProductLinkModel
from constraint_models.order_product_model import OrderProductModel
from constraints.constraint_main.constraint import Constraint
from constraints.constraint_main.custom_constraint import CustomConstraint
from constraints.models.example_models.pause_thread import PauseModel
from flask import Flask, request
import jsonpickle
from stage.stage import Stage, StageGroup
from task_pipeline.pipeline import Pipeline
from task_main.task import Task
from user import create_new_user
from constraint_models.internet_model import InternetModel
from constraint_models.product_description_model import ProductDescriptionModel
import json
from werkzeug.serving import WSGIRequestHandler
WSGIRequestHandler.protocol_version = "HTTP/1.1"

app = Flask(__name__)

all_users = {}
all_tasks = {}
all_stage_groups = {}
all_constraints = {
    "Exchange rate": CustomConstraint("Exchange rate", "View the current exchange rate between 2 currencies", InternetModel()),
    "Pause": CustomConstraint("Pause", "A constraint to pause", PauseModel()),
    "Product description": CustomConstraint("Product description", "View the product's basic information", ProductDescriptionModel()),
    "Order confirmation": CustomConstraint("Order confirmation", "This constraint confirms the order", OrderProductModel()),
    "Product link": CustomConstraint("Product link", "Provide a link to a URL for your customer", ProductLinkModel()),
    "Password": CustomConstraint("Password", "Requires a secret word/phrase before access can be granted", PasswordModel()),
    "Time range": CustomConstraint("Time range", "Set a time for where your task can be accessed.", TimeRangeModel()),
    "Chat": CustomConstraint("Chat", "Chat with your customers", ChatModel()),
    "Delivery": CustomConstraint("Delivery", "View the current delivery status", DeliveryModel())
}
all_constraint_views = {}


def create_constraint(constraint_name):
    if constraint_name == "Exchange rate":
        return CustomConstraint("Exchange rate", "View the current exchange rate between 2 currencies", InternetModel())
    elif constraint_name == "Pause":
        return CustomConstraint("Pause", "A constraint to pause", PauseModel())
    elif constraint_name == "Product description":
        return CustomConstraint("Product description", "View the product's basic information", ProductDescriptionModel())
    elif constraint_name == "Order confirmation":
        return CustomConstraint("Order confirmation", "This constraint confirms the order", OrderProductModel())
    elif constraint_name == "Product link":
        return CustomConstraint("Product link", "Provide a link to a URL for your customer", ProductLinkModel())
    elif constraint_name == "Password":
        return CustomConstraint("Password", "Requires a secret word/phrase before access can be granted", PasswordModel())
    elif constraint_name == "Time range":
        return CustomConstraint("Time range", "Set a time for where your task can be accessed.", TimeRangeModel())
    elif constraint_name == "Chat":
        return CustomConstraint("Chat", "Chat with your customers", ChatModel())
    elif constraint_name == "Delivery":
        return CustomConstraint("Delivery", "View the current delivery status", DeliveryModel())


@app.route('/')
def index():
    return f"all users: {all_users}, all tasks: {all_tasks}"


@app.route("/constraints")
def get_all_constraints():
    constraints = []
    for constraint in all_constraints:
        constraint_obj = all_constraints[constraint]
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
                "required": is_constraint_required

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


all_pipelines = {}


@app.route("/create_pipe")
def create_pipeline():
    task = None
    stage_group = None

    pipeline = Pipeline(task, stage_group)
    all_pipelines[pipeline.id] = pipeline


@app.route("/create_task", methods=["POST", "GET"])
def create_task():
    global all_stage_groups

    task_name = request.form["task_name"]
    task_desc = request.form["task_desc"]
    task_stage_group_id = request.form["stage_group_id"]
    stage_group = all_stage_groups[task_stage_group_id]

    task: Task = Task(task_name, task_desc)
    task.set_constraint_stage_config(stage_group)
    all_tasks[str(task.id)] = task

    return json.dumps({"task_id": str(task.id)})


@app.route("/task")
def get_all_tasks():
    global all_tasks
    return f"all tasks: {all_tasks}"


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
                "stage_group_id": str(task.constraint_stage_config.id)
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


@app.route("/stage_group", methods=["GET", "POST"])
def get_stage_groups():
    global all_stage_groups, all_constraints

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
                if constraint_name in all_constraints:
                    constraint_obj: Constraint = create_constraint(
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


@app.route("/stage_group/<stage_group_id>/<stage_name>", methods=["GET", "POST"])
def stage_details(stage_group_id, stage_name):
    global all_stage_groups, all_constraints
    if request.method == "GET":
        if stage_group_id in all_stage_groups:
            stage_group: StageGroup = all_stage_groups[stage_group_id]
            for stage in stage_group.stages:
                if stage.name == stage_name:
                    constraints = []
                    for constraint in stage.constraints:
                        is_constraint_required = constraint.model.input_count != 0

                        constraints.append({
                            "constraint_name": constraint.name,
                            "constraint_desc": constraint.description,
                            "config_inputs": constraint.configuration_inputs,
                            "required": is_constraint_required
                        })

                    return {
                        "stage_name": stage_name,
                        "constraints": constraints
                    }
    elif request.method == "POST":
        constraint_name = request.form["constraint_name"]
        if constraint_name in all_constraints:
            pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
