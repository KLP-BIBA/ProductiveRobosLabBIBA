#!/usr/bin/python3
"""Plays joint-space waypoints for every robot of the cell and publishes /joint_states.

If motions.yaml has an 'apple' section, the apple is published as markers on /cell/objects:
held by a gripper between a 'grasp' and a 'release' waypoint, otherwise lying on its spot.

Runs with the system Python on purpose: ROS Noetic's rospy belongs to /usr/bin/python3.

Private parameters:
  ~layout   path of cell_layout.yaml (robot ids and types)
  ~motions  path of motions.yaml (joint names per robot type, waypoints per robot, apple)
  ~animate  true: loop through the waypoints; false: hold the first waypoint
  ~speed    time factor of the motion, 1.0 = as written in motions.yaml
  ~rate     publishing rate in Hz
"""
import math
import xml.etree.ElementTree as ET

import rospy
import yaml
from sensor_msgs.msg import JointState
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray


def ease(s):
    """Cosine ease-in/ease-out on [0, 1]: robots start and stop without jerk."""
    return 0.5 - 0.5 * math.cos(math.pi * s)


class RobotMotion:
    """Waypoint loop of one robot. Each waypoint: move = seconds from the previous one, hold = seconds to stay."""

    def __init__(self, robot_id, joints, waypoints, offset):
        self.id = robot_id
        self.names = [robot_id + "_" + j for j in joints]
        self.waypoints = waypoints
        self.offset = offset
        self.cycle = sum(w["move"] + w["hold"] for w in waypoints)
        self.marks = []  # (arrival time in the robot's own loop, 'grasp' | 'release', spot)
        elapsed = 0.0
        for w in waypoints:
            if len(w["pose"]) != len(joints):
                raise ValueError(f"{robot_id}: waypoint '{w.get('name')}' has {len(w['pose'])} values, "
                                 f"expected {len(joints)}")
            for kind in ("grasp", "release"):
                if kind in w:
                    self.marks.append((elapsed + w["move"], kind, w[kind]))
            elapsed += w["move"] + w["hold"]

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


class Apple:
    """Where the apple is at a given time: held by a robot or lying on a spot."""

    def __init__(self, cfg, robots):
        self.radius = float(cfg.get("radius", 0.04))
        self.spots = {name: [float(v) for v in p] for name, p in cfg["spots"].items()}
        self.cycle = max(r.cycle for r in robots)
        if any(abs(r.cycle - self.cycle) > 1e-6 for r in robots):
            rospy.logwarn("robots have different loop times; the apple relay will drift")
        self.events = sorted(((t - r.offset) % r.cycle, kind, r.id, spot)
                             for r in robots for t, kind, spot in r.marks)
        if not self.events:
            rospy.logwarn("no grasp/release waypoints; the apple stays on its first spot")

    def state(self, t, animate):
        """('held', robot id) or ('lying', spot name)."""
        if not self.events:
            return "lying", next(iter(self.spots))
        if not animate:
            releases = [e for e in self.events if e[1] == "release"]
            return ("lying", releases[-1][3]) if releases else ("lying", self.events[0][3])
        tau = t % self.cycle
        past = [e for e in self.events if e[0] <= tau]
        _, kind, robot, spot = past[-1] if past else self.events[-1]
        return ("held", robot) if kind == "grasp" else ("lying", spot)


def apple_markers(apple, state, robot_ids, stamp):
    """Sphere, stem and leaf. Each holder has its own marker namespace, so no marker changes its frame."""
    out = MarkerArray()
    holders = ["lying"] + list(robot_ids)
    active = "lying" if state[0] == "lying" else state[1]
    for holder in holders:
        if holder == "lying":
            frame, centre, up = "world", apple.spots.get(state[1], [0, 0, 0]) if active == "lying" else [0, 0, 0], 1.0
        else:
            frame, centre, up = holder + "_gripper_grasp", [0.0, 0.0, 0.0], -1.0  # grasp frame z points down
        r = apple.radius
        parts = [  # id, type, offset from the centre, scale, colour
            (0, Marker.SPHERE, (0.0, 0.0, 0.0), (2 * r, 2 * r, 2 * r), (0.78, 0.08, 0.10)),
            (1, Marker.CYLINDER, (0.0, 0.0, up * (r + 0.008)), (0.007, 0.007, 0.025), (0.35, 0.22, 0.10)),
            (2, Marker.SPHERE, (0.012, 0.0, up * (r + 0.012)), (0.028, 0.013, 0.005), (0.20, 0.55, 0.15)),
        ]
        for pid, mtype, off, scale, rgb in parts:
            m = Marker()
            m.header.frame_id = frame
            m.header.stamp = stamp
            m.ns = "apple_" + holder
            m.id = pid
            if holder != active:
                m.action = Marker.DELETE
                out.markers.append(m)
                continue
            m.action = Marker.ADD
            m.type = mtype
            m.pose.position.x = centre[0] + off[0]
            m.pose.position.y = centre[1] + off[1]
            m.pose.position.z = centre[2] + off[2]
            m.pose.orientation.w = 1.0
            m.scale.x, m.scale.y, m.scale.z = scale
            m.color = ColorRGBA(rgb[0], rgb[1], rgb[2], 1.0)
            m.frame_locked = True
            out.markers.append(m)
    return out


def load_motions(layout, motions):
    result = []
    per_robot = motions.get("robots") or {}
    for robot in layout["robots"]:
        rtype = motions["types"].get(robot["type"])
        own = per_robot.get(robot["id"], {})
        waypoints = own.get("waypoints", (rtype or {}).get("waypoints"))
        if rtype is None or not waypoints:
            rospy.logerr("robot %s: no joints or waypoints for type '%s' in motions.yaml", robot["id"], robot["type"])
            continue
        result.append(RobotMotion(robot["id"], rtype["joints"], waypoints, float(own.get("offset", 0.0))))
    return result


def uncovered_joints(covered):
    """Movable joints of /robot_description that no motion drives (published as 0).

    Mimic joints (gripper linkage) are left out: robot_state_publisher derives them."""
    root = ET.fromstring(rospy.get_param("/robot_description"))
    movable = [j.get("name") for j in root.findall("joint")
               if j.get("type") in ("revolute", "continuous", "prismatic") and j.find("mimic") is None]
    return [j for j in movable if j not in covered]


def main():
    rospy.init_node("waypoint_player")
    with open(rospy.get_param("~layout")) as f:
        layout = yaml.safe_load(f)
    with open(rospy.get_param("~motions")) as f:
        motions = yaml.safe_load(f)
    animate = rospy.get_param("~animate", True)
    speed = float(rospy.get_param("~speed", 1.0))
    hz = float(rospy.get_param("~rate", 30.0))
    rate = rospy.Rate(hz)

    robots = load_motions(layout, motions)
    covered = [n for r in robots for n in r.names]
    rest = uncovered_joints(covered)
    if rest:
        rospy.logwarn("no waypoints for joints %s, publishing 0", rest)
    apple = Apple(motions["apple"], robots) if motions.get("apple") and robots else None
    rospy.loginfo("playing %d robots, %d joints, animate=%s, speed=%.2f, apple=%s",
                  len(robots), len(covered), animate, speed, "yes" if apple else "no")

    pub = rospy.Publisher("/joint_states", JointState, queue_size=1)
    marker_pub = rospy.Publisher("/cell/objects", MarkerArray, queue_size=1, latch=True)
    marker_every = max(1, int(round(hz / 10.0)))  # markers at about 10 Hz
    robot_ids = [r.id for r in robots]
    tick = 0
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
        if apple and tick % marker_every == 0:
            marker_pub.publish(apple_markers(apple, apple.state(t, animate), robot_ids, msg.header.stamp))
        tick += 1
        rate.sleep()


if __name__ == "__main__":
    main()
