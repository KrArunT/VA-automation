#!/bin/bash
export ANSIBLE_HOST_KEY_CHECKING=False
uv run ansible-playbook -i inventory.yml run_scripts.yml
