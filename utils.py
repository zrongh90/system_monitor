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
    db2_detail = DB2.query.filter_by(sys_inventory=inventory).all()
    for one_db in db2_info_list:
        inst_name_in = one_db["inst_name"]
        db_name_in = one_db["db_str"]
        listen_port_in = one_db["port_ouput"]
        update_only_flag = False
        for curr_db in db2_detail:
            # 当前数据库中包含inventory对应的数据库名，只更新对应数据
            if curr_db.db_name == db_name_in:
                app.logger.debug("update current db2 info for object id: " + curr_db.db2_info_id)
                curr_db.inst_name = inst_name_in
                curr_db.listen_port = int(listen_port_in)
                update_only_flag = True
            # 当前数据库中不包含数据库信息，新增数据库信息
            if not update_only_flag:
                new_db2 = DB2(inst_name=inst_name_in, db_name=db_name_in, listen_port=int(listen_port_in),
                              sys_inventory=str(inventory))
                app.logger.debug("insert new db2 info into database")
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
    was_detail = WebSphere.query.filter_by(sys_inventory=inventory).all()
    for one_was in was_info_list:
        prf_name_in = one_was['prf_path'].strip()
        srv_name_in = one_was['srv_name'].strip()
        curr_mem_in = one_was['mem']
        max_mem_in = one_was['max_mem']
        update_only_flag = False
        for curr_was in was_detail:
            # 当前数据库中包含该was信息，只更新其他数据
            if prf_name_in == curr_was.prf_name:
                app.logger.debug("update current was info for object id:" + curr_was.was_info_id)
                curr_was.srv_name = srv_name_in
                curr_was.max_mem = int(max_mem_in)
                curr_was.curr_mem = float(curr_mem_in)
                update_only_flag = True
        # 当前数据库中不包含目标was信息，新增was
        if not update_only_flag:
            new_was = WebSphere(max_mem=int(max_mem_in), curr_mem=float(curr_mem_in), prf_name=prf_name_in,
                                srv_name=srv_name_in, sys_inventory=str(inventory))
            app.logger.debug("insert new was object into database")
            app.logger.debug(new_was)
            db.session.add(new_was)


def inventory_sys_ansible_update(system_info, ansible_facts_result):
    """
    更新系统信息
    :param system_info: 待更新的系统信息
    :param ansible_facts_result: 通过ansible setup modules获取的系统信息
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
    """
    更新db2/was及系统信息的总调用方法
    :param sys_obj: 待更新信息的system对象
    :param details_host_ok: 通过ansible接口返回的facts及component信息
    :return:
    """
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

