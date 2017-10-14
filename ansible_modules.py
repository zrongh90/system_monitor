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
        inventory_was_ansible_update(was_info_list, host)


# ansible api template
def ansible_run(inventory_in):
    # "remote_user/permissions/debug_method" the global variable
    host_list = [].append(inventory_in)
    tasks_list = [dict(action=dict(module='shell', args=INFO_GET_SCRIPT))]
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
    pass
    # host_list = ['10.8.5.34','10.7.1.7','192.168.2.31','10.8.5.47','10.8.5.35','192.168.3.38','10.8.247.143','10.8.5.46','10.8.24.33','11.8.8.81','192.168.2.69','192.168.2.68','192.168.3.59','11.8.11.15','10.8.24.12','192.168.2.63','192.168.2.62','192.168.3.57','192.168.2.60','192.168.2.66','192.168.2.65','192.168.3.52','192.168.4.17','10.8.14.103','10.8.14.107','10.8.14.104','10.8.24.35','10.8.10.73','10.8.10.72','10.8.14.108','10.8.10.70','10.8.10.76','10.8.10.43','10.8.9.68','10.8.24.13','10.8.24.10','10.8.9.108','192.168.2.58','10.8.24.15','192.168.3.54','192.168.3.27','192.168.2.33','11.8.10.24','11.8.10.26','11.8.8.198','10.8.24.32','11.8.10.23','11.8.8.194','11.8.8.195','11.8.8.197','11.8.8.190','11.8.8.191','10.8.9.74','192.168.2.57','192.168.2.54','192.168.2.55','10.8.5.45','192.168.4.16','10.8.9.72','10.8.9.73','10.8.5.77','10.8.9.78','192.168.3.91','10.8.17.45','10.8.17.44','192.168.3.119','11.8.8.201','11.8.8.203','11.8.8.204','11.8.8.205','11.8.8.206','10.8.251.107','192.168.3.111','11.8.8.209','192.168.3.113','192.168.3.112','192.168.3.114','11.8.8.208','11.8.8.77','11.8.8.95','192.168.5.11','10.8.9.75','10.8.9.67','192.168.3.58','11.8.8.63','11.8.8.62','11.8.8.181','11.8.8.180','11.8.8.187','11.8.8.186','11.8.8.185','11.8.8.184','10.8.252.216','11.8.8.189','11.8.8.188','11.8.8.76','10.8.17.9','10.7.1.13','10.7.1.12','10.7.1.11','10.7.1.10','10.7.1.16','10.7.1.15','10.7.1.14','192.168.3.33','192.168.3.32','10.8.17.34','10.8.17.35','192.168.3.36','192.168.3.35','192.168.3.34','10.8.251.113','192.168.3.108','11.8.8.214','11.8.8.213','11.8.8.212','11.8.8.210','192.168.3.102','192.168.3.103','192.168.3.106','192.168.3.107','192.168.3.104','192.168.3.105','10.8.9.89','10.8.9.88','10.8.24.36','11.8.8.80','192.168.3.53','11.8.8.112','11.8.8.113','192.168.5.17','192.168.5.16','10.8.24.38','10.8.9.87','192.168.5.10','11.8.8.74','192.168.3.99','192.168.5.9','192.168.3.43','192.168.3.45','192.168.2.26','10.8.24.37','10.8.5.66','10.8.5.64','10.8.5.63','192.168.2.20','192.168.2.23','10.8.16.16','192.168.2.34','192.168.2.35','10.8.16.15','192.168.3.131','192.168.3.130','10.8.10.28','10.8.10.29','192.168.3.84','192.168.3.85','192.168.3.83','192.168.3.139','192.168.3.138','11.8.8.176','192.168.5.28','10.8.252.111','192.168.3.90','192.168.5.22','192.168.5.23','10.8.9.90','192.168.5.26','10.8.10.71','192.168.5.24','192.168.5.25','10.8.5.78','10.7.1.6','10.7.1.5','10.7.1.4','10.7.1.3','10.7.1.2','10.7.1.1','11.8.8.75','10.8.9.59','10.7.1.9','10.7.1.8','192.168.5.13','10.8.17.14','10.8.17.15','10.8.17.16','10.8.17.17','10.8.17.18','10.8.17.19','10.8.10.74','10.8.5.54','192.168.3.120','192.168.3.98','192.168.2.25','192.168.3.123','192.168.3.124','192.168.3.125','192.168.3.126','192.168.3.127','192.168.3.128','11.8.8.177','192.168.3.93','11.8.8.175','192.168.3.95','192.168.3.97','192.168.3.96','10.8.24.11','192.168.3.92','10.8.24.34','10.8.5.52','11.8.8.147','10.8.252.243','192.168.2.14','192.168.3.55','11.8.8.146','10.8.24.65','192.168.2.22','10.8.24.2','10.8.24.3','10.8.24.4','10.8.24.5','10.8.24.6','10.8.24.7','10.8.24.8','192.168.3.46','10.8.9.33','10.8.9.34','192.168.3.47','192.168.2.41','192.168.3.60','11.8.8.141','192.168.3.62','192.168.2.15','192.168.3.89','11.8.8.96','192.168.3.39','11.8.8.163','11.8.8.162','11.8.8.103','192.168.2.42','10.8.10.44','11.8.8.102','10.8.9.66','11.8.8.101','10.8.9.79','192.168.4.34','192.168.4.33','10.8.1.177','192.168.2.3','11.8.8.105','192.168.3.81','192.168.3.31','10.8.9.43','192.168.2.5','192.168.3.77','11.8.8.83','11.8.8.157','11.8.8.158','11.8.8.159','192.168.3.78','192.168.3.146','192.168.3.145','192.168.3.142','192.168.3.141','10.8.9.107','10.8.9.26','192.168.5.19','192.168.4.20','192.168.4.23','192.168.4.22','192.168.4.25','192.168.4.24','192.168.4.26','192.168.5.20','192.168.2.32','10.8.24.31','11.8.8.67','10.8.252.162','10.8.247.251','10.8.9.58','10.8.247.252','192.168.2.19','192.168.2.74','192.168.2.75','10.8.24.9','10.8.252.68','10.8.24.67','10.8.24.66','11.8.8.145','11.8.8.143','11.8.8.142','11.8.8.228','11.8.8.140','11.8.8.226','192.168.3.48','192.168.3.49','10.8.14.111','10.8.9.76','11.8.8.220','11.8.10.15','10.8.4.3','10.8.4.2','11.8.10.17','11.8.8.104']
# tasks_list = [
# 	dict(action=dict(module='shell', args="python /zxyx/utils/was_get.py"))]
# ansible_run(host_list, tasks_list)
