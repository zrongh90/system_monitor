# -*- coding: UTF-8 -*-
#!/usr/bin/env python

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
from utils import inventory_was_ansible_update, inventory_db2_ansible_update, my_log

# script in target machine to return websphere info
INFO_GET_SCRIPT = u'python /zxyx/utils/get_component.py'
REPORTER_INVENTORY = u'10.8.1.86'
REPORTER_USER = u'db2inst1'
# TODO: use pycrypto module to encode the password
REPORTER_PASSWD = u'passw0rd'
return_json_str = None


class TivoliResultCallback(CallbackBase):
    host_ok = []

    def _init_(self, *args, **kwargs):
        self.host_ok = []

    def v2_runner_on_ok(self, result, **kwargs):
        my_log(result._result['stdout_lines'])
        self.host_ok = result._result['stdout_lines']

    def get_host_ok(self):
        return self.host_ok


# ansible callback method for details_ansible_run method to
# supdate the was and db2 modules for select inventory
class DetailResultCallback(CallbackBase):
    """
    ansible callback method for details_ansible_run method to
    supdate the was and db2 modules for select inventory
    """
    # TODO: use gather facts to update system info
    def v2_runner_on_ok(self, result, **kwargs):
        host = result._host
        component_info_list = result._result['stdout_lines']
        for one_component in component_info_list:
            one_component_dict = eval(one_component)
            was_json = json.loads(one_component_dict['was'])
            if was_json["status"] == "success":
                inventory_was_ansible_update(was_json["msg"], host)
            db2_json = json.loads(one_component_dict['db2'])
            if db2_json["status"] == "success":
                inventory_db2_ansible_update(db2_json["msg"], host)


def ansible_run_api(inventory_in, tasks_list, call_back_class, input_options, input_passwd_dict):
    """
    Ansible api to other method to call
    :param inventory_in: IP to connect to run task
    :param tasks_list: tasks to run
    :param call_back_class: how to deal with target's return
    :param input_options: ansible options, such as become,forks,remote_user etc
    :param input_passwd_dict: password for target
    :return:
    """
    host_list = [inventory_in]

    my_log("ansible run")
    my_log("inventory_in: " + inventory_in)

    # initialize needed objects
    variable_manager = VariableManager()
    loader = DataLoader()

    options = input_options

    passwords = input_passwd_dict
    my_log(passwords)

    # create inventory and pass to var manager
    inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=host_list)
    variable_manager.set_inventory(inventory)

    # create play with tasks
    play_source = dict(
        name='ansible run',
        hosts='all',
        gather_facts="no",
        tasks=tasks_list
    )
    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    # actually run it
    tqm = None

    results_callback = call_back_class
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
        return_host_ok = tqm._stdout_callback.get_host_ok()
    finally:
        if tqm is not None:
            tqm.cleanup()
    return return_host_ok


def get_default_option():
    """Generate default option
    :return:
    """
    in_remote_user = 'ansible'
    in_is_become = 'yes'
    in_become_method = 'sudo'
    in_become_user = 'root'
    Options = namedtuple('Options',
                         ['connection', 'module_path', 'forks', 'sudo', 'remote_user', 'become', 'become_method',
                          'become_user', 'check'])
    my_options = Options(connection=C.DEFAULT_TRANSPORT, module_path=None, forks=100, sudo=None,
                         remote_user=in_remote_user, become=in_is_become, become_method=in_become_method,
                         become_user=in_become_user, check=False)
    return my_options, dict(vault_pass='secret')


def details_ansible_run(inventory_in):
    """ Ansible method to get modules
    ansible method to get inventory's modules, currently support for db2 and was
    :param inventory_in: the inventory to get details
    :returns None
    """
    tasks_list = [dict(action=dict(module='shell', args=INFO_GET_SCRIPT))]
    ansible_run_api(inventory_in, tasks_list, DetailResultCallback(), get_default_option())


def tivoli_ansible_run(tivoli_clear_shell):
    """ Ansible Method to clear tivoli alert
    clear tivoli reporter system(IP:10.8.1.86) alert accord to shell
    :param tivoli_clear_shell: input shell to clear
    :return:
    """
    inventory_in = REPORTER_INVENTORY
    in_remote_user = 'db2inst1'
    in_dict_passwd = dict(conn_pass=REPORTER_PASSWD)
    tasks_list = [dict(action=dict(module='shell', args=tivoli_clear_shell))]
    Options = namedtuple('Options',
                         ['connection', 'module_path', 'forks', 'sudo', 'remote_user', 'become', 'become_method',
                          'become_user', 'check'])
    my_options = Options(connection=C.DEFAULT_TRANSPORT, module_path=None, forks=100, sudo=None,
                         remote_user=in_remote_user, become=None, become_method=None,
                         become_user=None, check=False)
    return ansible_run_api(inventory_in, tasks_list, TivoliResultCallback(), my_options, in_dict_passwd)


def ansible_collect(inventory_in, collect_cmd_str):
    """
    input collect cmd string and use ansible to collect the scirpt to to collect db or was log
    :param inventory_in: IP to deal
    :param collect_cmd_str:  shell to call in remote machine
    :return:
    """
    tasks_list = [dict(action=dict(module='shell', args=collect_cmd_str))]
    ansible_run_api(inventory_in, tasks_list, get_default_option())


if __name__ == '__main__':
    #details_ansible_run("192.168.3.145")
    #details_ansible_run("10.8.5.35")
    #details_ansible_run("10.8.5.46")
    return_host_ok = tivoli_ansible_run("python /home/db2inst1/alert_ctl.py content Ethernet110/1/20端口运行状态改变")
    print(return_host_ok)
    # print(return_str)
