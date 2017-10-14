from modules import db, System, WebSphere, DB2


def inventory_was_ansible_update(was_info_list=None, inventory=None):
    for one_was in was_info_list:
        if one_was.split('|').__len__() != 4 or one_was.find("servers") == -1:
            print("Error to parse was detail")
            exit(1)
        _, was, max_mem, curr_mem = one_was.split('|')
        prf_path, server = was.split('=')[1].replace('configuration', '').split('servers')
        max_mem_in = max_mem.replace('-Xmx', '').replace('m', '')
        curr_mem_in = curr_mem.replace('mem%', '')
        prf_name_in = prf_path
        srv_name_in = server.replace('/', '')
        new_was = WebSphere(max_mem=max_mem_in, curr_mem=curr_mem_in, prf_name=prf_name_in, srv_name=srv_name_in,
                            sys_inventory=inventory)
        print("insert new was object (" + new_was + ") into database")
        db.session.add(new_was)


def ansible_get(component=None, inventory=None):
    sys_info = None
    was_info_list = None
    was_info = [u'|-Dosgi.configuration.area=/o2oAppNode01/servers/o2onode03_cust/configuration|-Xmx4096m|mem%9.0',
                u'|-Dosgi.configuration.area=/o2oAppNode01/servers/o2onode03_busi/configuration|-Xmx4096m|mem%6.0',
                u'|-Dosgi.configuration.area=/o2oAppNode01/servers/o2onode03_pay/configuration|-Xmx2048m|mem%6.5',
                u'|-Dosgi.configuration.area=/o2oAppNode01/servers/o2onode03_ycyw/configuration|-Xmx2048m|mem%6.2']
    # db2_info_list = None
    # initial one was object and save to database
    for one_was in was_info:
        _, was, max_mem, curr_mem = one_was.split('|')
        prf_path, server = was.split('=')[1].replace('configuration', '').split('servers')
        max_mem_in = max_mem.replace('-Xmx', '').replace('m', '')
        curr_mem_in = curr_mem.replace('mem%', '')
        prf_name_in = prf_path
        srv_name_in = server.replace('/', '')
        new_was = WebSphere(max_mem=max_mem_in, curr_mem=curr_mem_in,
                            prf_name=prf_name_in, srv_name=srv_name_in, sys_inventory=inventory)
        # db.session.add(new_was)

        # TODO: ansible get function，return System/WebSphere/DB2 object
        # info_update(inventory, sys_info, was_info_list, db2_info_list)


def sys_update(system_info, new_sys_info):
    if system_info is None:
        exit(1)
    else:
        # update system info
        system_info.hostname = new_sys_info.hostname
        system_info.os_info = new_sys_info.os_info
        system_info.platform = new_sys_info.platform
        system_info.cpu_num = new_sys_info.cpu_num
        db.session.commit()


def was_update(inventory, new_was_info_list):
    was_info = db.session.query(WebSphere).filter(inventory=inventory).all()
    # delete was info in db, not need to keep old was info
    for one_was in was_info:
        db.session.delete(one_was)
    for one_new_was in new_was_info_list:
        db.session.add(one_new_was)
    db.session.commit()


def db2_update(inventory, db2_info_list):
    pass


def info_update(inventory=None, new_sys_info=None, websphere_list=None, db2_list=None):
    system_info = db.session.query(System).filter(inventory=inventory).first()
    sys_update(system_info, new_sys_info)
    was_update(inventory, websphere_list)
    db2_update(inventory, db2_list)
