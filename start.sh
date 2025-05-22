# #!/bin/bash
# export ANSIBLE_HOST_KEY_CHECKING=False
# uv run ansible-playbook -i inventory.yml run_scripts.yml

#!/bin/bash
scp start_va.sh va_amd:/home/amd/workspace/vademo
ssh va_amd  "/home/amd/workspace/vademo/start_va.sh"
