docker build -t va_demo_ws_server:latest .
docker run --rm \
  -it \
  -p 8768:8768 \
  -p 15672:15672 \
  -e ANSIBLE_HOST_KEY_CHECKING=False \
  va_demo_ws_server:latest
