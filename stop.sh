# #!/bin/bash
# export ANSIBLE_HOST_KEY_CHECKING=False
# uv run ansible-playbook -i inventory.yml kill_scripts.yml

scp stop_va.sh va_amd:/home/amd/workspace/vademo
ssh va_amd  "/home/amd/workspace/vademo/stop_va.sh"
