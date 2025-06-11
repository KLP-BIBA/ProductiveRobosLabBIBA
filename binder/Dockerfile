# Dockerfile of the base image: https://github.com/IntEL4CoRo/docker-stacks/blob/master/Dockerfile
FROM intel4coro/base-notebook:20.04-noetic-vnc

# Path to the default ROS workspace
ENV ROS_WS=/home/workspace/ros

# Test von KLP jetzt auskommentiert
USER root
RUN apt install -y ros-noetic-pr2-gazebo
#RUN apt update && apt install -y ros-kinetic-pr2-gazebo

# Initiate ROS workspace 

WORKDIR ${ROS_WS}/src
# A Workaround for fixing the issue of RvizWeb loading meshes with "file:///" path instead of "package:///".
COPY --chown=${NB_USER}:users binder/me ${ROS_WS}/src/me
#COPY --chown=${NB_USER}:users launch/mujoco_config ${ROS_WS}/src/me/config
COPY --chown=${NB_USER}:users binder/noetic.rosinstall /home/${NB_USER}/noetic.rosinstall
RUN wstool merge /home/${NB_USER}/noetic.rosinstall \
  && wstool update

#============= Install extra software packages =============#
# Examples:
# RUN apt update && apt install -y curl
# RUN pip install numpy
#===========================================================#

# Copy content to the image
ENV REPO_DIR=${HOME}/work
WORKDIR ${REPO_DIR}
COPY --chown=${NB_USER}:users . ${REPO_DIR}/

# Create a symbolic link to the ROS workspace under the working directory
RUN ln -s ${ROS_WS} ${PWD}/ROS_WS

# The entrypoint of the docker image
COPY --chown=${NB_USER}:users binder/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

