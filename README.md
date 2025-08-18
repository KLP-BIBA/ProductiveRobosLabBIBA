# Run this in a local Docker:

```bash
export GID=$(id -g) && xhost +local:docker && docker compose -f ./binder/docker-compose.yml up  --build && xhost -local:docker
```