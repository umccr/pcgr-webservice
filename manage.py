from flask_script import Manager, Server
from server import create_app

app = create_app()
manager = Manager(app)
manager.add_command("runserver", Server(host="0.0.0.0"))

if __name__ == '__main__':
    manager.run()
