# -*- coding: UTF-8 -*-
from modules import db, System, WebSphere, DB2, app
import json


def inventory_db2_ansible_update(db2_info_list=None, inventory=None):
    """
    通过ansible返回结果更新数据库内的db2信息
    :param db2_info_list: ansible返回的系统DB2信息列表
    :param inventory:  目标系统IP
    :return: None
    """
    app.logger.debug("run into db2 info update")
    for one_db in db2_info_list:
        inst_name_in = one_db["inst_name"]
        db_name_in = one_db["db_str"]
        listen_port_in = one_db["port_ouput"]
        new_db2 = DB2(inst_name=inst_name_in, db_name=db_name_in, listen_port=int(listen_port_in),
                      sys_inventory=str(inventory))
        app.logger.debug(new_db2)
        db.session.add(new_db2)


def inventory_was_ansible_update(was_info_list=None, inventory=None):
    """
    通过ansible返回结果更新数据库的websphere信息
    :param was_info_list: ansible返回的系统WebSphere信息列表
    :param inventory: 目标系统IP
    :return: None
    """
    app.logger.debug("run into was info update")
    for one_was in was_info_list:
        prf_name_in = one_was['prf_path']
        curr_mem_in = one_was['mem']
        max_mem_in = one_was['max_mem']
        srv_name_in = one_was['srv_name']
        new_was = WebSphere(max_mem=int(max_mem_in), curr_mem=float(curr_mem_in), prf_name=prf_name_in,
                            srv_name=srv_name_in,
                            sys_inventory=str(inventory))
        app.logger.debug(new_was)
        app.logger.debug("insert new was object into database")
        db.session.add(new_was)


def inventory_sys_ansible_update(system_info, ansible_facts_result):
    """
    更新系统信息
    :param system_info:
    :param new_sys_info:
    :return:
    """
    if system_info is None:
        exit(1)
    else:
        # update system info
        system_info.hostname = ansible_facts_result.get("ansible_hostname")
        system_info.os_info = ansible_facts_result.get("ansible_distribution_version")
        system_info.platform = ansible_facts_result.get("ansible_product_name")
        system_info.cpu_num = ansible_facts_result.get("ansible_processor_vcpus")

def detail_update(sys_obj, details_host_ok):
    ansible_stdout_lines = details_host_ok["stdout_lines"]
    for one_component in ansible_stdout_lines:
        one_component_dict = eval(one_component)
        was_json = json.loads(one_component_dict["was"])
        if was_json["status"] == "success":
            inventory_was_ansible_update(was_json["msg"], details_host_ok["host"])
        db2_json = json.loads(one_component_dict["db2"])
        if db2_json["status"] == "success":
            inventory_db2_ansible_update(db2_json["msg"], details_host_ok["host"])
    ansible_facts = details_host_ok["ansible_facts"]
    inventory_sys_ansible_update(sys_obj, ansible_facts)

