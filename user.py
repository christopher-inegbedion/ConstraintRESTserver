import uuid


class User:
    def __init__(self, name):
        self.id = str(uuid.uuid4())
        self.name = name
        self.pipeline = None

    def set_pipeline(self, pipeline):
        self.pipeline = pipeline


def create_new_user(name):
    return User(name)
