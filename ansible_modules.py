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
from modules import app
from utils import inventory_was_ansible_update, inventory_db2_ansible_update

# script in target machine to return websphere info
INFO_GET_SCRIPT = u'python /zxyx/utils/get_component.py'
REPORTER_INVENTORY = u'10.8.1.86'
REPORTER_USER = u'db2inst1'
# TODO: use pycrypto module to encode the password
REPORTER_PASSWD = u'passw0rd'
GATHER_FACTS = u'yes'
NOT_GATHER_FACTS = u'no'

return_json_str = None


class ResultCallback(CallbackBase):
    """
    ansible的默认回调处理方法，针对不同的结果写入字典中
    """
    host_ok = {}

    def _init_(self, *args, **kwargs):
        self.host_ok = {}

    def v2_runner_on_ok(self, result, **kwargs):
        if "stdout_lines" in result._result:
            app.logger.debug(result._result['stdout_lines'])
            self.host_ok["stdout_lines"] = result._result["stdout_lines"]
            self.host_ok["host"] = result._host
        elif "ansible_facts" in result._result:
            app.logger.debug(result._result["ansible_facts"])
            self.host_ok["ansible_facts"] = result._result["ansible_facts"]

    def v2_runner_on_failed(self, result, **kwargs):
        app.logger.debug("run into ansible failed")
        for i in result._result:
            app.logger.debug(result._result[i])

    def v2_runner_on_unreachable(self, result, **kwargs):
        app.logger.debug("run into ansible unreadched")
        for i in result._result:
            app.logger.debug(result._result[i])

    def get_host_ok(self):
        return self.host_ok


def ansible_run_api(inventory_in, tasks_list, input_options, input_passwd_dict, is_gather_facts):
    """
    Ansible api to other method to call
    :param is_gather_facts:
    :param inventory_in: IP to connect to run task
    :param tasks_list: tasks to run
    :param input_options: ansible options, such as become,forks,remote_user etc
    :param input_passwd_dict: password for target
    :return:
    """
    host_list = [inventory_in]

    app.logger.debug("ansible run\ninventory_in: {0}".format(inventory_in))
    app.logger.debug(tasks_list)

    # initialize needed objects
    variable_manager = VariableManager()
    loader = DataLoader()
    options = input_options
    passwords = input_passwd_dict

    # create inventory and pass to var manager
    inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=host_list)
    variable_manager.set_inventory(inventory)

    # create play with tasks
    play_source = dict(
        name='ansible run',
        hosts='all',
        gather_facts=is_gather_facts,
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
        host_ok_result = tqm._stdout_callback.get_host_ok()
    finally:
        if tqm is not None:
            tqm.cleanup()
    return host_ok_result


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
    return my_options


def script_issue_ansible_run(inventory_in, script_name):
    """
    通过ansible进行脚本的下发到tmp目录，保存目标机器端的脚本与服务器一致
    :param inventory_in: 需要下发的主机IP
    :param script_name: 需要下发的脚本名称
    :return:
    """
    copy_args = "src=./scripts/{0} dest=/tmp/ mode=0644 owner=root".format(script_name)
    tasks_list = [dict(action=dict(module="copy", args=copy_args))]
    return ansible_run_api(inventory_in=inventory_in, tasks_list=tasks_list, input_options=get_default_option(),
                           input_passwd_dict=dict(vault_pass='secret'), is_gather_facts=NOT_GATHER_FACTS)


def sys_perf_ansible_run(inventory_in):
    """
    通过ansible接口收集系统信息，包括iostat, vmstat, df, netstat等信息
    :param inventory_in: 需要收集的系统Inventory
    :return:
    """
    # TODO: 所有目标主机新增获取系统信息的python
    perf_args = "python /zxyx/utils/get_perf.py"
    tasks_list = [dict(action=dict(module="shell", args=perf_args))]
    return ansible_run_api(inventory_in=inventory_in, tasks_list=tasks_list, input_options=get_default_option(),
                           input_passwd_dict=dict(valut_ass='secret'), is_gather_facts=NOT_GATHER_FACTS)


def details_ansible_run(inventory_in):
    """ Ansible method to get modules
    ansible method to get inventory's modules, currently support for db2 and was
    :param inventory_in: the inventory to get details
    :returns None
    """
    tasks_list = [dict(action=dict(module='shell', args=INFO_GET_SCRIPT))]
    return ansible_run_api(inventory_in, tasks_list, get_default_option(), dict(vault_pass='secret'), GATHER_FACTS)


def tivoli_ansible_run(tivoli_clear_shell):
    """ Ansible Method to clear tivoli alert
    clear tivoli reporter system(IP:10.8.1.86) alert accord to shell
    :param tivoli_clear_shell: input shell to clear
    :return:
    """
    inventory_in = REPORTER_INVENTORY
    in_remote_user = 'db2inst1'
    in_dict_passwd = dict(conn_pass=REPORTER_PASSWD)
    tasks_list = [
        dict(action=dict(module='shell', args=tivoli_clear_shell))
    ]
    Options = namedtuple('Options',
                         ['connection', 'module_path', 'forks', 'sudo', 'remote_user', 'become', 'become_method',
                          'become_user', 'check'])
    my_options = Options(connection=C.DEFAULT_TRANSPORT, module_path=None, forks=100, sudo=None,
                         remote_user=in_remote_user, become=None, become_method=None,
                         become_user=None, check=False)
    return ansible_run_api(inventory_in, tasks_list, my_options, in_dict_passwd, NOT_GATHER_FACTS)


def ansible_collect(inventory_in, collect_cmd_str):
    """
    input collect cmd string and use ansible to collect the scirpt to to collect db or was log
    :param inventory_in: IP to deal
    :param collect_cmd_str:  shell to call in remote machine
    :return:
    """
    tasks_list = [dict(action=dict(module='shell', args=collect_cmd_str))]
    return ansible_run_api(inventory_in, tasks_list, get_default_option(), dict(vault_pass='secret'), NOT_GATHER_FACTS)


if __name__ == '__main__':
    # details_ansible_run("192.168.3.145")
    # details_ansible_run("10.8.5.35")
    # details_ansible_run("10.8.5.46")
    # return_host_ok = tivoli_ansible_run("python /home/db2inst1/alert_ctl.py content Ethernet110/1/20端口运行状态改变")
    return_host_ok = script_issue_ansible_run("10.8.1.86", "alert_ctl.py")
    print(return_host_ok)
    # print(return_str)
