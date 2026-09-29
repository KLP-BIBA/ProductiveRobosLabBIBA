cmake_minimum_required(VERSION 3.0.2)
project(biba_cell_description)

find_package(catkin REQUIRED)
catkin_package()

# The lab runs from the devel space; scripts/waypoint_player.py is found there as an
# executable file of the package. The install rules only matter for an install space.
install(PROGRAMS scripts/waypoint_player.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
install(DIRECTORY config launch rviz urdf
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
