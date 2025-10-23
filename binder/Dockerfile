# Dockerfile of the base image: https://github.com/IntEL4CoRo/docker-stacks/blob/master/Dockerfile
FROM intel4coro/base-notebook:20.04-noetic-vnc

# Path to the default ROS workspace
ENV ROS_WS=${HOME}/workspace/ros

# Test von KLP jetzt auskommentiert
USER root
RUN apt install -y ros-noetic-pr2-gazebo \
        ros-noetic-rqt
#RUN apt update && apt install -y ros-kinetic-pr2-gazebo

# Initiate ROS workspace 

WORKDIR ${ROS_WS}/src
# A Workaround for fixing the issue of RvizWeb loading meshes with "file:///" path instead of "package:///".
COPY --chown=${NB_USER}:users binder/me ${ROS_WS}/src/me
#COPY --chown=${NB_USER}:users launch/mujoco_config ${ROS_WS}/src/me/config
COPY --chown=${NB_USER}:users binder/noetic.rosinstall /home/${NB_USER}/noetic.rosinstall
# Upgrade wstool in case version is too old
RUN pip install --upgrade wstool

# Remove src and .rosinstall to start fresh
RUN rm -rf /home/${NB_USER}/workspace/ros/src/* /home/${NB_USER}/workspace/ros/.rosinstall

# Initialize workspace instead of merging
RUN export WSTOOL_NONINTERACTIVE=1 && \
    wstool init /home/${NB_USER}/workspace/ros/ /home/${NB_USER}/noetic.rosinstall && \
    wstool update --delete-changed-uris

# Optional: Verify version
RUN wstool --version && which wstool

#============= Install extra software packages =============#
# Examples:
# RUN apt update && apt install -y curl
# RUN pip install numpy
#===========================================================#

RUN mkdir -p ${HOME}/work/src

# Copy your source code before building (usually good practice)
ENV REPO_DIR=${HOME}/work
WORKDIR ${REPO_DIR}
COPY --chown=${NB_USER}:users . ${REPO_DIR}/

# Create the symbolic link for convenience
RUN ln -s ${ROS_WS} ${PWD}/ROS_WS

# Now build your actual ROS workspace: 
# source ROS environment to find catkin and dependencies, 
# then build your ROS workspace with catkin build.
WORKDIR ${ROS_WS}
RUN /bin/bash -c "source /opt/ros/noetic/setup.bash && catkin build"


# The entrypoint of the docker image
COPY --chown=${NB_USER}:users binder/webapps.json ${ROS_WS}/src/rvizweb/webapps/app.json
COPY --chown=${NB_USER}:users binder/entrypoint.sh /entrypoint.sh

WORKDIR ${HOME}

ENTRYPOINT ["/entrypoint.sh"]

