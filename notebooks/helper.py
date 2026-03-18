from pathlib import Path
from typing import Any, Callable, Dict, Iterable, TypedDict
import ipywidgets as widgets
import subprocess


def check_file(file: Path | str, ending: str = "", parameter_name: str = "") -> Path:
    message_prefix = (
        f"Parameter {parameter_name}" if parameter_name != "" else "Given File"
    )
    try:
        file = Path(file)
    except:
        raise ValueError(f"{message_prefix} must be a valid file path")
    if not file.is_file():
        raise ValueError(f"{message_prefix} must be pointing to an existing file")
    if ending != "" and not file.match("*" + ending):
        raise ValueError(f"{message_prefix} must be pointing to an {ending} file")
    return file


Robot = TypedDict("Robot", {"name": str, "path": Path, "description": str | None})


class Robots:
    def __init__(self):
        self.robots_store: Dict[str, Robot] = {}

    def register(
        self, robot_name: str, urdf_file: Path | str, description: str | None = None
    ):
        if robot_name == None:
            raise ValueError("Parameter robot_name must be not None")
        try:
            robot_name = str(robot_name)
        except:
            raise ValueError("Parameter robot_name must be of type str")
        if robot_name == "":
            raise ValueError("Parameter robot_name must to be not empty")
        urdf_file = check_file(
            file=urdf_file,
            ending=".urdf",
            parameter_name="urdf_file",
        )

        if self.robots_store.get(robot_name):
            raise ValueError(f"Robot {robot_name} is already registerd")
        self.robots_store[robot_name] = Robot(
            name=robot_name, path=urdf_file, description=description
        )

    def get_robots(self) -> Iterable[str]:
        return self.robots_store.keys()

    def get_urdf_file(self, robot_name: str) -> str | None:
        robot = self.robots_store.get(robot_name)
        return robot.get("path") if robot else None

    def get_description(self, robot_name: str) -> str | None:
        robot = self.robots_store.get(robot_name)
        return robot.get("description") if robot else None

    def get_selection_widget(self, create_button_fn):
        def create_description_widget(descrition: str | None = None):
            return widgets.HTML(
                value=descrition or "<em>Keine Beschreibung verfügbar</em>"
            )

        return widgets.GridBox(
            sum(
                [
                    [
                        create_button_fn(robot["name"]),
                        create_description_widget(robot["description"]),
                    ]
                    for robot in self.robots_store.values()
                ],
                [],
            ),
            layout=widgets.Layout(
                grid_template_columns="25% 75%",
                align_items="center",
                grid_gap="5px 10px",
            ),
        )

class Rvizweb:
    def __init__(
        self, make_sidecar: Callable[[], Any], iframe, display: Callable[[Any], None]
    ):
        if iframe == None:
            raise ValueError("Parameter iframe must not be None")
        self.make_sidecar = make_sidecar
        self.display = display
        self.iframe = iframe
        self.sidecar = None

    def open(self):
        if self.sidecar != None:
            self.sidecar.close()
        self.sidecar = self.make_sidecar()
        with self.sidecar:
            self.display(self.iframe)


class Launcher:
    COMMAND_TEMPLATE = "roslaunch {launch_file} urdf_file:={urdf_file}"

    def __init__(self, launch_file: Path | str):
        launch_file = check_file(
            file=launch_file, ending=".launch", parameter_name="launch_file"
        )
        self.launch_command_builder = lambda urdf_file: self.COMMAND_TEMPLATE.format(
            launch_file=launch_file,
            urdf_file=urdf_file,
        )
        self.open_process: subprocess.Popen | None = None
        self.process_name: str | None = None

    def launch(
        self,
        urdf_file: Path | str,
        rvizweb: Rvizweb,
        process_name: str | None = None,
        ferr=None,
        fout=None,
    ):
        if self.open_process:
            self.open_process.kill()
        self.open_process = subprocess.Popen(
            ["/bin/bash", "-c", self.launch_command_builder(urdf_file=urdf_file)],
            stdout=fout if fout else subprocess.DEVNULL,
            stderr=ferr if ferr else subprocess.DEVNULL,
            shell=False,
        )
        self.process_name = process_name if process_name else "Unknown"
        rvizweb.open()

    def kill(self):
        self.open_process.kill()
        self.open_process = None
        self.process_name = None

    def get_process_name(self) -> str | None:
        return self.process_name
