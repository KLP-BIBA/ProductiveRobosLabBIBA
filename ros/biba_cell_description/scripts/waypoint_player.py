#!/usr/bin/python3
"""Plays joint-space waypoints for every robot of the cell and publishes /joint_states.

Runs with the system Python on purpose: ROS Noetic's rospy belongs to /usr/bin/python3.

Private parameters:
  ~layout   path of cell_layout.yaml (robot ids and types)
  ~motions  path of motions.yaml (waypoints per robot type, optional per-robot overrides)
  ~animate  true: loop through the waypoints; false: hold the first waypoint
  ~speed    time factor of the motion, 1.0 = as written in motions.yaml
  ~rate     publishing rate in Hz
"""
import math
import xml.etree.ElementTree as ET

import rospy
import yaml
from sensor_msgs.msg import JointState


def ease(s):
    """Cosine ease-in/ease-out on [0, 1]: robots start and stop without jerk."""
    return 0.5 - 0.5 * math.cos(math.pi * s)


class RobotMotion:
    """Waypoint loop of one robot. Each waypoint: move = seconds from the previous one, hold = seconds to stay."""

    def __init__(self, prefix, joints, waypoints, offset):
        self.names = [prefix + j for j in joints]
        self.waypoints = waypoints
        self.offset = offset
        self.cycle = sum(w["move"] + w["hold"] for w in waypoints)
        for w in waypoints:
            if len(w["pose"]) != len(joints):
                raise ValueError(f"{prefix}: waypoint '{w.get('name')}' has {len(w['pose'])} values, "
                                 f"expected {len(joints)}")

    def positions(self, t, animate):
        if not animate or len(self.waypoints) < 2 or self.cycle <= 0:
            return list(self.waypoints[0]["pose"])
        t = (t + self.offset) % self.cycle
        for i, w in enumerate(self.waypoints):
            start = self.waypoints[i - 1]["pose"]  # i == 0 starts from the last waypoint
            if t < w["move"]:
                s = ease(t / w["move"])
                return [a + (b - a) * s for a, b in zip(start, w["pose"])]
            t -= w["move"]
            if t < w["hold"]:
                return list(w["pose"])
            t -= w["hold"]
        return list(self.waypoints[-1]["pose"])


def load_motions(layout, motions):
    result = []
    overrides = motions.get("robots") or {}
    for robot in layout["robots"]:
        rtype = motions["types"].get(robot["type"])
        if rtype is None:
            rospy.logerr("robot %s: no motion for type '%s' in motions.yaml", robot["id"], robot["type"])
            continue
        own = overrides.get(robot["id"], {})
        result.append(RobotMotion(prefix=robot["id"] + "_", joints=rtype["joints"],
                                  waypoints=own.get("waypoints", rtype["waypoints"]),
                                  offset=float(own.get("offset", 0.0))))
    return result


def uncovered_joints(covered):
    """Movable joints of /robot_description that no motion drives (published as 0)."""
    root = ET.fromstring(rospy.get_param("/robot_description"))
    movable = [j.get("name") for j in root.findall("joint")
               if j.get("type") in ("revolute", "continuous", "prismatic")]
    return [j for j in movable if j not in covered]


def main():
    rospy.init_node("waypoint_player")
    with open(rospy.get_param("~layout")) as f:
        layout = yaml.safe_load(f)
    with open(rospy.get_param("~motions")) as f:
        motions = yaml.safe_load(f)
    animate = rospy.get_param("~animate", True)
    speed = float(rospy.get_param("~speed", 1.0))
    rate = rospy.Rate(float(rospy.get_param("~rate", 30.0)))

    robots = load_motions(layout, motions)
    covered = [n for r in robots for n in r.names]
    rest = uncovered_joints(covered)
    if rest:
        rospy.logwarn("no waypoints for joints %s, publishing 0", rest)
    rospy.loginfo("playing %d robots, %d joints, animate=%s, speed=%.2f",
                  len(robots), len(covered), animate, speed)

    pub = rospy.Publisher("/joint_states", JointState, queue_size=1)
    t0 = rospy.get_time()
    while not rospy.is_shutdown():
        t = (rospy.get_time() - t0) * speed
        msg = JointState()
        msg.header.stamp = rospy.Time.now()
        for r in robots:
            msg.name.extend(r.names)
            msg.position.extend(r.positions(t, animate))
        msg.name.extend(rest)
        msg.position.extend([0.0] * len(rest))
        pub.publish(msg)
        rate.sleep()


if __name__ == "__main__":
    main()
