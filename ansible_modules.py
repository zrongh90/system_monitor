#!/usr/bin/env python

## @file
# File description:
# This file is password management system,contains ansible api module.
# @authors: RedHat
# @date: 03/16/2017
# @update:
# @use: command: python drc_pms <ostype> <username> <password> <ip_lists> 
# @note: System type support only input "aix/rhel"
#        Ansible versions 2.x
#
# version: 1.0

import sys
import crypt
import json
import getpass
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from ansible import constants as C

# ansible default ssh user,need to be combined with the configuration 'permissions'.
from utils import inventory_was_ansible_update

# script in target machine to return websphere info
# TODO: add get db2 and system info to this script
INFO_GET_SCRIPT = u'python /zxyx/utils/was_get.py'

remote_user = 'ansible'
# general user permissions config: sudo/become/default
permissions = 'become'
# debug method config: off/on/ansible_default
debug_method = 'on'


class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """

    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        was_info_list = result._result['stdout_lines']
	print(host)
        print(was_info_list)
        inventory_was_ansible_update(was_info_list, host)


# ansible api template
def ansible_run(inventory_in):
    # "remote_user/permissions/debug_method" the global variable
    host_list = [ inventory_in ]
    tasks_list = [dict(action=dict(module='shell', args=INFO_GET_SCRIPT))]
    print("ansible run")
    print("iventory_in: " + inventory_in)
    Options = namedtuple('Options',
                         ['connection', 'module_path', 'forks', 'sudo', 'remote_user', 'become', 'become_method',
                          'become_user', 'check'])
    # initialize needed objects
    variable_manager = VariableManager()
    loader = DataLoader()

    options = Options(connection=C.DEFAULT_TRANSPORT, module_path=None, forks=100, sudo=None, remote_user=remote_user,
                      become='yes', become_method='sudo', become_user='root', check=False)

    passwords = dict(vault_pass='secret')

    # create inventory and pass to var manager
    inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=host_list)
    variable_manager.set_inventory(inventory)

    # create play with tasks
    play_source = dict(
        name='get_was_info',
        hosts='all',
        gather_facts="no",
        tasks=tasks_list
    )
    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    # actually run it
    tqm = None

    results_callback = ResultCallback()
    try:
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=options,
            passwords=passwords,
            stdout_callback=results_callback,

        )
        result = tqm.run(play)
    finally:
        if tqm is not None:
            tqm.cleanup()


if __name__ == '__main__':
	ansible_run("192.168.3.105")
