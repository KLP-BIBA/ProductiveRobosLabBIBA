# Run this in a local Docker:

```bash
export GID=$(id -g) && xhost +local:docker && docker compose -f ./binder/docker-compose.yml up  --build && xhost -local:docker
```

# Sources

We still figure out to display our robots and therfore we use some files from an others:

- <https://github.com/chhinze/urdf_scene_nicegui> is used to display the Osaca robot, to figure out to dispay URDF files with `.stl` meshes
- <https://github.com/ros/urdf_tutorial/tree/master/urdf> is used to figure out how to display URDF files with `.dae` meshes