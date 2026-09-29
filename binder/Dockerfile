# Dockerfile of the base image: https://github.com/IntEL4CoRo/docker-stacks/blob/master/Dockerfile
FROM intel4coro/base-notebook:20.04-noetic-vnc

# Path to the default ROS workspace. The base image ships it already built
# (rvizweb, rosboard, interactive_marker_proxy); the steps below add to it.
ENV ROS_WS=${HOME}/workspace/ros

USER root

WORKDIR ${ROS_WS}/src
# A Workaround for fixing the issue of RvizWeb loading meshes with "file:///" path instead of "package:///".
COPY --chown=${NB_USER}:users binder/me ${ROS_WS}/src/me

# Upgrade wstool in case version is too old
RUN pip install --upgrade wstool

#KLP added
RUN apt update && apt install -y \
    ros-noetic-universal-robots \
    ros-noetic-moveit \
    ros-noetic-trac-ik \
    ros-noetic-trac-ik-kinematics-plugin \
    libassimp-dev \
    assimp-utils \
    python3-pip

RUN apt update && apt install -y \
    ros-noetic-industrial-core \
    ros-noetic-industrial-robot-client \
    ros-noetic-industrial-robot-status-controller

# Source packages (FANUC incl. CR-35iA and the MoveIt configs, OnRobot grippers), pinned to
# commits in binder/noetic.rosinstall and cloned into ${ROS_WS}/src next to the base packages.
COPY --chown=${NB_USER}:users binder/noetic.rosinstall /home/${NB_USER}/noetic.rosinstall
RUN export WSTOOL_NONINTERACTIVE=1 && \
    wstool merge -t ${ROS_WS}/src -y /home/${NB_USER}/noetic.rosinstall && \
    wstool update -t ${ROS_WS}/src fanuc onrobot

# Build workspace (cached until one of the steps above changes)
RUN /bin/bash -c "source /opt/ros/noetic/setup.bash && cd ${ROS_WS} && catkin build"

RUN pip install --no-cache-dir pyassimp

# Optional: Verify version
RUN wstool --version && which wstool

#============= Install extra software packages =============#
# Examples:
# RUN apt update && apt install -y curl
# RUN pip install numpy
# PR2 simulation for the rvizweb example (launch/pr2_example.launch)
RUN apt-get update && apt-get install -y ros-noetic-pr2-gazebo && rm -rf /var/lib/apt/lists/*
#===========================================================#

# Copy your source code before building (usually good practice)
ENV REPO_DIR=${HOME}/work
WORKDIR ${REPO_DIR}
COPY --chown=${NB_USER}:users . ${REPO_DIR}/

# Create the symbolic link for convenience
RUN ln -s ${ROS_WS} ${PWD}/ROS_WS

# Lab packages from this repository. Only these are built after the COPY above, so a push
# that changes notebooks or meshes does not rebuild the whole workspace.
#KLP added
COPY --chown=${NB_USER}:users my_robot_description ${ROS_WS}/src/my_robot_description
# Linked instead of copied: edits to the cell layout in JupyterLab apply at the next launch.
RUN ln -s ${REPO_DIR}/ros/biba_cell_description ${ROS_WS}/src/biba_cell_description
WORKDIR ${ROS_WS}
RUN /bin/bash -c "source /opt/ros/noetic/setup.bash && catkin build my_robot_description biba_cell_description"

# KLP added
RUN echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc && \
    echo "source /home/jovyan/workspace/ros/devel/setup.bash" >> ~/.bashrc

# The entrypoint of the docker image
COPY --chown=${NB_USER}:users binder/webapps.json ${ROS_WS}/src/rvizweb/webapps/app.json
COPY --chown=${NB_USER}:users binder/entrypoint.sh /entrypoint.sh

WORKDIR ${HOME}

ENTRYPOINT ["/entrypoint.sh"]
