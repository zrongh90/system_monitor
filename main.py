# -*- coding: UTF-8 -*-
from flask import render_template, request, jsonify, url_for, flash
from sqlalchemy import distinct
from werkzeug.utils import redirect
from time import sleep

# from ansible_modules import ansible_collect
from modules import System, WebSphere, DB2, app, db

# from ansible_modules import ansible_run
# from ansible_modules import tivoli_ansible_run
from utils import my_log

NUM_PER_PAGE = 11


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html")


@app.errorhandler(405)
def page_not_found(error):
    return render_template("404.html")


@app.errorhandler(500)
def page_not_found(error):
    return render_template("500.html")


# 获取数据库中对应的操作系统类型列表，并进行排序
def get_os_list():
    os_list = list(x[0] for x in set(db.session.query(distinct(System.os_info)).all()))
    os_list.sort()
    return os_list


@app.route('/')
def get_all_system():
    sys_was_count_list = []
    sys_db2_count_list = []
    page = request.args.get('page', 1, type=int)
    # 对结果进行分页
    paginate = System.query.paginate(page, NUM_PER_PAGE)
    systems = paginate.items
    for one_system in systems:
        sys_was_count = WebSphere.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_db2_count = DB2.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_was_count_list.append(sys_was_count)
        sys_db2_count_list.append(sys_db2_count)
    db.session.close()

    return render_template("all_system.html", inventory_filter_val="", title="主机信息列表", system_list=systems,
                           pagination=paginate, os_filter_val="", os_list_val=get_os_list(),
                           sys_was_count_list=sys_was_count_list, sys_db2_count_list=sys_db2_count_list)


@app.route('/filter', methods=['POST', 'GET'])
def get_filter_system(inventory_filter=None, os_filter=None):
    """
    获取过滤后的系统信息，可以根据（inventory/os)进行过滤
    :param inventory_filter: IP过滤器
    :param os_filter: 操作系统类型过滤器
    :return: details.html
    """
    my_log("filter")
    sys_was_count_list = []
    sys_db2_count_list = []
    if request.method == 'POST':
        inventory_filter = request.form['inventory_filter']
        os_filter = request.form['os_filter']
        my_log("POST")
    elif request.method == 'GET':
        inventory_filter = request.args.get('inventory_filter')
        os_filter = request.args.get('os_filter')
        my_log("GET")
    my_log("inventory_filter:" + inventory_filter)
    my_log("os_filter:" + os_filter)
    page = request.args.get('page', 1, type=int)
    # 对结果进行分页
    if os_filter == "all":
        paginate = System.query.filter(System.inventory.like("%" + inventory_filter + "%")).paginate(page, NUM_PER_PAGE)
    else:
        paginate = System.query.filter(System.inventory.like("%" + inventory_filter + "%")). \
            filter(System.os_info == str(os_filter)).paginate(page, NUM_PER_PAGE)
    systems = paginate.items
    for one_system in systems:
        sys_was_count = WebSphere.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_db2_count = DB2.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_was_count_list.append(sys_was_count)
        sys_db2_count_list.append(sys_db2_count)
    db.session.close()
    my_log(systems)
    return render_template("all_system.html", inventory_filter_val=inventory_filter, title="主机信息列表",
                           system_list=systems, pagination=paginate, os_filter_val=os_filter, os_list_val=get_os_list(),
                           sys_was_count_list=sys_was_count_list, sys_db2_count_list=sys_db2_count_list)


@app.route('/detail/<inventory>')
def detail(inventory=None):
    """
    传统的获取系统信息的方法
    根据系统的inventory获取系统信息，was信息和db2信息并渲染details.html返回
    :param inventory: 系统IP
    :return: details.html: 系统详细信息页面，包括系统信息/was/db2信息
    """
    try:
        system_detail = System.query.filter_by(inventory=inventory).first_or_404()
        was_detail = WebSphere.query.filter_by(sys_inventory=inventory).all()
        db2_detail = DB2.query.filter_by(sys_inventory=inventory).all()
        # 删除数据库中目前有的was信息
        my_log("remove current websphere info")
        # for one_was in was_detail:
        #     db.session.delete(one_was)
        # for one_db2 in db2_detail:
        #     db.session.delete(one_db2)
        # call ansible function to retrieve websphere,db2,system info for target inventory
        # current only realize get websphere info
        # details_ansible_run(inventory_in=inventory)
        # db.session.commit()
        new_was_detail = WebSphere.query.filter_by(sys_inventory=inventory).all()
        new_db2_detail = DB2.query.filter_by(sys_inventory=inventory).all()
        my_log(new_db2_detail)
        return render_template("details.html", title="具体信息", system_detail_in=system_detail,
                               was_detail_in=new_was_detail,
                               db2_detail_in=new_db2_detail)
    except Exception as e:
        my_log(e)
        # 更新失败，立刻回滚
        db.session.rollback()
        return render_template("500.html")


@app.route('/tivoli')
def tivoli():
    return render_template("tivoli.html")


@app.route('/clear_tivoli_alert', methods=['POST'])
def clear_tivoli_alert(event_id=None, event_ip=None, event_content=None):
    """
    根据条件，手工将tivoli监控reporter数据库的目标记录状态修改为0
    :param event_id: 事件ID
    :param event_ip: 事件IP
    :param event_content: 事件内容
    :return: result: 清理结果
    """
    tivoli_python_path = "python /home/db2inst1/alert_ctl.py "
    my_log("run into tivoli alert clear")
    # TODO: 多条件匹配问题，需要将获取数据分割，同时将ansible操作剥离
    event_id = request.form.get('event_id', None, type=str)
    event_ip = request.form.get('event_ip', None, type=str)
    event_content = request.form.get('event_content', None, type=str)
    if event_id:
        my_log(event_id)
        condition = " id " + str(event_id)
    if event_ip:
        my_log(event_ip)
        condition = " ip " + event_ip
    if event_content:
        my_log(event_content)
    condition = " content \"" + event_content + "\""
    tivoli_cmd = tivoli_python_path + condition
    my_log(tivoli_cmd)
    # return_host_ok = tivoli_ansible_run(tivoli_cmd)
    return_host_ok = []
    if len(return_host_ok) == 0:
        flash("no record match event: " + event_content, 'info')
    for msg in return_host_ok:
        # msg = "success update tivoli for event_content: " + str(event_content)
        flash(msg, 'success')
    return redirect(url_for('tivoli'))
    # return render_template("tivoli.html")


# 通过jquery获取系统的WAS信息
# input: invent_val
# return: serialized WebSphere Object
@app.route('/_get_was')
def jquery_get_was_info():
    inventory_input = request.args.get('invent_val', 0, type=str)
    my_log("inventory_input:" + inventory_input)
    was_detail = WebSphere.query.filter_by(sys_inventory=inventory_input)
    return jsonify(result=[i.serialize for i in was_detail.all()])


# 通过jquery获取系统的DB2信息
# input: invent_val
# return: serialized DB2 Object
@app.route('/_get_db2')
def jquery_get_db2_info():
    inventory_input = request.args.get('invent_val', None, type=str)
    my_log("inventory_input:" + inventory_input)
    db2_detail = DB2.query.filter_by(sys_inventory=inventory_input)
    return jsonify(result=[i.serialize for i in db2_detail.all()])


@app.route('/_collect_sys')
def jquery_collect_system(sys_inven=None):
    """
    通过jquery 调用ansible接口访问主机并调用linux_perf脚本收集系统信息
    :param sys_inven: 目标主机IP
    :return: result: 收集结果
    """
    my_log("into system perf collect!")
    sys_inven = request.args.get('sys_inven', None, type=str)
    my_log("do with inventory:" + sys_inven)
    # TODO: call ansible api to run linux_perf script
    sleep(5)
    return jsonify(result="success")


@app.route('/_collect_db2')
def jquery_collect_db2(db_inven=None, db_name=None, inst_name=None):
    """
    通过jquery调用ansile接口收集DB2信息
    :param db_inven: 收集DB2日志的系统IP
    :param db_name: 收集的数据库
    :param inst_name: 数据库的实例名称
    :return: result： 收集结果
    """
    db_inven = request.args.get('db_inven', None, type=str)
    db_name = request.args.get('db_name', None, type=str)
    inst_name = request.args.get('inst_name', None, type=str)
    db2_collect_cmd_str = "su - " + inst_name + " -c \"/zxyx/collect/get_db2_log.sh " + inst_name \
                          + " \'\' " + db_name + "\""
    my_log(db2_collect_cmd_str)
    # TODO: call ansible to run command to collect db2 snapshot and pd
    # ansible_collect(db_inven, db2_collect_cmd_str)
    # return jsonify(result=[i.serialize for i in db2_detail.all()])
    sleep(2)
    return jsonify(result="test")


@app.route('/_collect_was')
def jquery_collect_was(was_inven=None, prf_name=None, srv_name=None):
    """
    通过jquery调用ansible接口获取收集websphere信息
    :param was_inven: websphere所在主机IP
    :param prf_name: websphere的概要文件名
    :param srv_name: websphere的应用服务器名
    :return: result: 收集结果
    """
    was_inven = request.args.get('was_inven', None, type=str)
    prf_name = request.args.get('prf_name', None, type=str)
    srv_name = request.args.get('srv_name', None, type=str)
    my_log(was_inven + ' ' + prf_name + ' ' + srv_name)
    sleep(5)
    return jsonify(result="success")


if __name__ == '__main__':
    app.debug = True
    # import sys
    # reload(sys)
    # sys.setdefaultencoding('utf8')
    app.run(host='0.0.0.0')
