# -*- coding: UTF-8 -*-
from modules import db, System, WebSphere, DB2, app


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


def sys_update(system_info, new_sys_info):
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
        system_info.hostname = new_sys_info.hostname
        system_info.os_info = new_sys_info.os_info
        system_info.platform = new_sys_info.platform
        system_info.cpu_num = new_sys_info.cpu_num
        db.session.commit()


# def was_update(inventory, new_was_info_list):
#     was_info = db.session.query(WebSphere).filter(inventory=inventory).all()
#     # delete was info in db, not need to keep old was info
#     for one_was in was_info:
#         db.session.delete(one_was)
#     for one_new_was in new_was_info_list:
#         db.session.add(one_new_was)
#     db.session.commit()
#
#
# def db2_update(inventory, db2_info_list):
#     pass
#
#
# def info_update(inventory=None, new_sys_info=None, websphere_list=None, db2_list=None):
#     system_info = db.session.query(System).filter(inventory=inventory).first()
#     sys_update(system_info, new_sys_info)
#     was_update(inventory, websphere_list)
#     db2_update(inventory, db2_list)



