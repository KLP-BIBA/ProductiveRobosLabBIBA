#!/bin/bash

source ${HOME}/workspace/ros/devel/setup.bash
roscore &

sleep 5

roslaunch rvizweb rvizweb.launch &

# Prepare temporary launch file with arg definition
MY_LAUNCH=$HOME/work/launch/my-first.launch
TMP_LAUNCH=/tmp/my-first.launch

cp $MY_LAUNCH $TMP_LAUNCH

# Insert <arg name="urdf_file" default="..." /> if missing
if ! grep -q '<arg name="urdf_file"' $TMP_LAUNCH; then
  sed -i '1i\<arg name="urdf_file" default="'"$HOME"'/work/urdf/my-first.urdf" />' $TMP_LAUNCH
fi

# Launch with argument pointing to your urdf file path
roslaunch $TMP_LAUNCH urdf_file:=$HOME/work/urdf/my-first.urdf &

# rest of your startup

exec "$@"

