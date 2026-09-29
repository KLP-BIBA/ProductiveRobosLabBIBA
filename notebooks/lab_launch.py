"""Start and stop a ROS launch file from a notebook and show RVizWeb next to it.

Used by PR2_rvizweb_example.ipynb and Cell_CR35iA_UR20.ipynb; the older notebooks use helper.py.
All scenes share one ROS master, so only one scene should run at a time.
"""
import os
import signal
import subprocess
import time
from pathlib import Path

import ipywidgets as widgets
import rospy
from IPython.display import IFrame, display
from sidecar import Sidecar

RVIZWEB_CONFIG = "/rvizweb/global_config"
RVIZWEB_CONFIG_SAVED = "/rvizweb/global_config_before_lab_launch"


def set_rvizweb_config(config_file):
    """RVizWeb reads this configuration when its page loads. The previous one is kept for restore."""
    if not rospy.has_param(RVIZWEB_CONFIG_SAVED):
        rospy.set_param(RVIZWEB_CONFIG_SAVED, rospy.get_param(RVIZWEB_CONFIG))
    rospy.set_param(RVIZWEB_CONFIG, Path(config_file).read_text())


def restore_rvizweb_config():
    if rospy.has_param(RVIZWEB_CONFIG_SAVED):
        rospy.set_param(RVIZWEB_CONFIG, rospy.get_param(RVIZWEB_CONFIG_SAVED))
        rospy.delete_param(RVIZWEB_CONFIG_SAVED)


def cleanup_after_scene():
    """Remove what a stopped scene leaves behind on the ROS master.

    Gazebo scenes set /use_sim_time to true; later scenes without a simulation clock would
    wait forever. Nodes that did not unregister in time stay listed until rosnode cleanup.
    """
    if rospy.has_param("/use_sim_time"):
        rospy.delete_param("/use_sim_time")
    subprocess.run("echo y | rosnode cleanup", shell=True, capture_output=True, timeout=60)


def wait_for_param(name, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if rospy.has_param(name):
            return True
        time.sleep(1)
    return False


class RosLaunch:
    """One roslaunch process. Stopped with SIGINT, so roslaunch also shuts down its nodes.

    args: list of roslaunch arguments, or a function returning that list at start time.
    """

    def __init__(self, args, log_file):
        self.args = args
        self.log_file = Path(log_file)
        self.process = None

    def running(self):
        return self.process is not None and self.process.poll() is None

    def start(self):
        self.stop()
        args = self.args() if callable(self.args) else self.args
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "w") as log:
            self.process = subprocess.Popen(["roslaunch", *[str(a) for a in args]], stdout=log,
                                            stderr=subprocess.STDOUT, start_new_session=True)

    def stop(self, timeout=20):
        if self.running():
            os.killpg(self.process.pid, signal.SIGINT)
            try:
                self.process.wait(timeout)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
        self.process = None


class LaunchPanel:
    """Start and Stop buttons for one launch file; RVizWeb opens in a panel on the right."""

    def __init__(self, title, launch_args, rvizweb_config=None, log_file=None, wait_s=60):
        self.title = title
        self.rvizweb_config = rvizweb_config
        self.wait_s = wait_s
        log_file = log_file or Path.home() / ".ros" / f"{title.replace(' ', '_')}.log"
        self.launch = RosLaunch(launch_args, log_file)
        self.sidecar = None
        self.start_button = widgets.Button(description=f"Start {title}", button_style="success",
                                           layout=widgets.Layout(width="auto", height="40px"))
        self.stop_button = widgets.Button(description="Stop", button_style="warning",
                                          layout=widgets.Layout(width="auto", height="40px"))
        self.status = widgets.HTML("Not started.")
        self.start_button.on_click(lambda _: self.start())
        self.stop_button.on_click(lambda _: self.stop())

    def start(self):
        self.status.value = "Starting ..."
        self.launch.stop()
        if rospy.has_param("/robot_description"):
            rospy.delete_param("/robot_description")  # detect the new model, not a leftover one
        if self.rvizweb_config:
            set_rvizweb_config(self.rvizweb_config)
        self.launch.start()
        if not wait_for_param("/robot_description", self.wait_s):
            self.status.value = f"No robot_description after {self.wait_s} s. Log: {self.launch.log_file}"
            return
        time.sleep(3)  # let robot_state_publisher send the first transforms
        self.open_rvizweb()
        self.status.value = f"Running. Log: <code>{self.launch.log_file}</code>"

    def stop(self):
        self.launch.stop()
        cleanup_after_scene()
        restore_rvizweb_config()
        if self.sidecar is not None:
            self.sidecar.close()
            self.sidecar = None
        self.status.value = "Stopped."

    def open_rvizweb(self):
        if self.sidecar is not None:
            self.sidecar.close()
        self.sidecar = Sidecar(title=f"RVizWeb: {self.title}", anchor="split-right")
        with self.sidecar:
            display(IFrame(src=rospy.get_param("/rvizweb/jupyter_proxy_url"), width="100%", height="100%"))

    def show(self):
        display(widgets.VBox([widgets.HBox([self.start_button, self.stop_button]), self.status]))
