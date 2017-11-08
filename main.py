# -*- coding: UTF-8 -*-
from flask import render_template, request, jsonify, url_for, flash
from sqlalchemy import distinct
from werkzeug.utils import redirect
from time import sleep
import logging.handlers
# from ansible_modules import ansible_collect
from modules import System, WebSphere, DB2, app, db
from utils import detail_update


NUM_PER_PAGE = 11
LOG_FILE = 'main.log'
PRODUCT = False
# from ansible_modules import ansible_run
if PRODUCT:
    from ansible_modules import tivoli_ansible_run, details_ansible_run, ansible_collect, script_issue_ansible_run, \
        sys_perf_ansible_run


def init_log():
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1024*1024, backupCount=5)
    fmt = "%(asctime)s - %(filename)s:%(lineno)s - %(module)s:%(funcName)s - %(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)


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


@app.route('/all_websphere', methods=['GET'])
def get_all_websphere(page=None):
    """
    分页获取websphere的信息列表
    :param page: 当前分页
    :return: 分页后的结果列表及分页信息
    """
    app.logger.debug("run into get_all_websphere function")
    page = request.args.get('page', 1, type=int)
    paginate = db.session.query(WebSphere, System).join(System).order_by(System.inventory).paginate(page, NUM_PER_PAGE)
    was_list_in = paginate.items
    return render_template("all_websphere.html", title="WebSphere中间件信息列表",
                           pagination=paginate, was_list=was_list_in)


@app.route('/all_db2', methods=['GET'])
def get_all_db2(page=None):
    """
    分页获取DB2的信息列表
    :param page: 当前分页
    :return: 分页后的结果列表及分页信息
    """
    app.logger.debug("run into get_all_db2 function")
    page = request.args.get('page', 1, type=int)
    paginate = db.session.query(DB2, System).join(System).paginate(page, NUM_PER_PAGE)
    db2_list_in = paginate.items
    return render_template("all_db2.html", title="DB2信息列表",
                           pagination=paginate, db2_list=db2_list_in)


@app.route('/filter', methods=['POST', 'GET'])
def get_filter_system(inventory_filter=None, os_filter=None):
    """
    获取过滤后的系统信息，可以根据（inventory/os)进行过滤
    :param inventory_filter: IP过滤器
    :param os_filter: 操作系统类型过滤器
    :return: details.html
    """
    app.logger.debug("filter")
    sys_was_count_list = []
    sys_db2_count_list = []
    if request.method == 'POST':
        inventory_filter = request.form['inventory_filter']
        os_filter = request.form['os_filter']
        app.logger.debug("POST")
    elif request.method == 'GET':
        inventory_filter = request.args.get('inventory_filter')
        os_filter = request.args.get('os_filter')
        app.logger.debug("GET")
    app.logger.debug("inventory_filter: {0}".format(inventory_filter))
    app.logger.debug("os_filter: {0}".format(os_filter))
    page = request.args.get('page', 1, type=int)
    # 对结果进行分页
    if os_filter == "all":
        paginate = System.query.filter(System.inventory.like("%{0}%".format(inventory_filter))).paginate(page, NUM_PER_PAGE)
    else:
        paginate = System.query.filter(System.inventory.like("%{0}%".format(inventory_filter))). \
            filter(System.os_info == str(os_filter)).paginate(page, NUM_PER_PAGE)
    systems = paginate.items
    for one_system in systems:
        sys_was_count = WebSphere.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_db2_count = DB2.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_was_count_list.append(sys_was_count)
        sys_db2_count_list.append(sys_db2_count)
    db.session.close()
    app.logger.debug(systems)
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
        if PRODUCT:
            # 删除数据库中目前有的was/db2信息
            # app.logger.debug("remove current WebSphere/DB2 info")
            # for one_was in was_detail:
            #     db.session.delete(one_was)
            # for one_db2 in db2_detail:
            #     db.session.delete(one_db2)
            # call ansible function to retrieve websphere,db2,system info for target inventory
            # current only realize get websphere info
            details_host_ok = details_ansible_run(inventory_in=inventory)
            app.logger.debug(system_detail)
            detail_update(system_detail, details_host_ok)
        db.session.commit()
        # app.logger.debug(details_host_ok)
        new_was_detail = WebSphere.query.filter_by(sys_inventory=inventory).all()
        new_db2_detail = DB2.query.filter_by(sys_inventory=inventory).all()
        return render_template("details.html", title="具体信息", system_detail_in=system_detail,
                               was_detail_in=new_was_detail,
                               db2_detail_in=new_db2_detail)
    except Exception as e:
        app.logger.debug(e)
        # 更新失败，立刻回滚
        db.session.rollback()
        return render_template("500.html")


@app.route('/tivoli')
def tivoli():
    return render_template("tivoli.html")


def deal_tivoli_condition(in_condition):
    """
    处理清理tivoli报警的抽象方法
    :param in_condition: 具体操作语句，例如" id 12345"或" content 测试"等
    :return:
    """
    tivoli_python_path = "python /home/db2inst1/alert_ctl.py "
    tivoli_cmd = tivoli_python_path + in_condition
    app.logger.debug(tivoli_cmd)
    return_host_ok = {"stdout_lines": ""}
    if PRODUCT:
        return_host_ok = tivoli_ansible_run(tivoli_cmd)
        app.logger.debug(return_host_ok)
    if len(return_host_ok["stdout_lines"]) == 0:
        flash("no record match event: {0} info".format(in_condition))
    else:
        for msg in return_host_ok["stdout_lines"]:
            flash(msg, 'success')


@app.route('/clear_tivoli_alert', methods=['POST'])
def clear_tivoli_alert(event_id=None, event_ip=None, event_content=None):
    """
    根据条件，手工将tivoli监控reporter数据库的目标记录状态修改为0
    :param event_id: 事件ID
    :param event_ip: 事件IP
    :param event_content: 事件内容
    :return: result: 清理结果
    """

    app.logger.debug("run into tivoli alert clear")
    event_id = request.form.get('event_id', None, type=str)
    event_ip = request.form.get('event_ip', None, type=str)
    event_content = request.form.get('event_content', None, type=str)
    if len(event_id):
        for one_id in event_id.split(','):
            if one_id.isdigit():
                condition = " id {0}".format(str(one_id).strip())
                deal_tivoli_condition(condition)
            else:
                flash("Alert ID: {0} not allow".format(one_id), 'error')
    if len(event_ip):
        for one_ip in event_ip.split(','):
            condition = " ip {0}".format(str(one_ip).strip())
            deal_tivoli_condition(condition)
    if len(event_content):
        for one_content in event_content.split(','):
            condition = " content \"{0}\"".format(str(one_content).strip())
            deal_tivoli_condition(condition)
    return redirect(url_for('tivoli'))


@app.route('/_get_was')
def jquery_get_was_info():
    # 通过jquery获取系统的WAS信息
    # input: invent_val
    # return: serialized WebSphere Object
    inventory_input = request.args.get('invent_val', 0, type=str)
    app.logger.debug("inventory_input: {0}".format(inventory_input))
    was_detail = WebSphere.query.filter_by(sys_inventory=inventory_input)
    return jsonify(result=[i.serialize for i in was_detail.all()])


@app.route('/_get_db2')
def jquery_get_db2_info():
    # 通过jquery获取系统的DB2信息
    # input: invent_val
    # return: serialized DB2 Object
    inventory_input = request.args.get('invent_val', None, type=str)
    app.logger.debug("inventory_input: {0}".format(inventory_input))
    db2_detail = DB2.query.filter_by(sys_inventory=inventory_input)
    return jsonify(result=[i.serialize for i in db2_detail.all()])


@app.route('/_collect_sys')
def jquery_collect_system(sys_inven=None):
    """
    通过jquery 调用ansible接口访问主机并调用linux_perf脚本收集系统信息
    :param sys_inven: 目标主机IP
    :return: result: 收集结果展示
    """
    app.logger.debug("into system perf collect!")
    sys_inven = request.args.get('sys_inven', None, type=str)
    app.logger.debug("do with inventory: {0}".format(sys_inven))
    perf_result = {}
    if PRODUCT:
        perf_result = sys_perf_ansible_run(sys_inven)
    else:
        perf_result["stdout_lines"] = [u'test', u'test2']
    return jsonify(result='\n'.join(perf_result["stdout_lines"]))


@app.route('/_collect_db2')
def jquery_collect_db2(db_inven=None, db_name=None, inst_name=None):
    """
    通过jquery调用ansile接口收集DB2信息
    :param db_inven: 收集DB2日志的系统IP
    :param db_name: 收集的数据库
    :param inst_name: 数据库的实例名称
    :return: result： 收集结果
    """
    app.logger.debug("run into jquery_collect_db2 function")
    db_inven = request.args.get('db_inven', None, type=str)
    db_name = request.args.get('db_name', None, type=str)
    inst_name = request.args.get('inst_name', None, type=str)
    db2_collect_cmd_str = "su - {0} -c \"sh /zxyx/collect/get_db2_log.sh {0} '' {1}\"".format(inst_name, db_name)
    app.logger.debug(db2_collect_cmd_str)
    collect_result = {}
    if PRODUCT:
        collect_result = ansible_collect(db_inven, db2_collect_cmd_str)
    else:
        collect_result["stdout_lines"] = [u'uid=1002(wlpcinst) gid=2001(db2iadm) groups=2001(db2iadm)', u'collect the 0 time snapshot and pd', u'', u'   Database Connection Information', u'', u' Database server        = DB2/LINUXX8664 10.5.5', u' SQL authorization ID   = WLPCINST', u' Local database alias   = PIRADB', u'', u'Sending -addnode output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092839', u'Sending -temptable output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092839', u'-quiesceinfo option is only available in Shared Data (SD) configurations.', u'Sending all options output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092839.', u'collect the 1 time snapshot and pd', u'', u'   Database Connection Information', u'', u' Database server        = DB2/LINUXX8664 10.5.5', u' SQL authorization ID   = WLPCINST', u' Local database alias   = PIRADB', u'', u'Sending -addnode output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092848', u'Sending -temptable output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092848', u'-quiesceinfo option is only available in Shared Data (SD) configurations.', u'Sending all options output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092848.', u'collect the 2 time snapshot and pd', u'', u'   Database Connection Information', u'', u' Database server        = DB2/LINUXX8664 10.5.5', u' SQL authorization ID   = WLPCINST', u' Local database alias   = PIRADB', u'', u'Sending -addnode output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092858', u'Sending -temptable output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092858', u'-quiesceinfo option is only available in Shared Data (SD) configurations.', u'Sending all options output to /tmp/zxyx/wlpcdbs_db2_171025092834/pdeverything.log.092858.', u'###########start to tar and gzip log#################wlpcdbs_db2_171025092834/', u'wlpcdbs_db2_171025092834/pdeverything.log.092858', u'wlpcdbs_db2_171025092834/snapshot.log.092835', u'wlpcdbs_db2_171025092834/snapshot.log.092854', u'wlpcdbs_db2_171025092834/snapshot.log.092845', u'wlpcdbs_db2_171025092834/pdeverything.log.092839', u'wlpcdbs_db2_171025092834/pdeverything.log.092848', u'wlpcdbs_db2_171025092834/db2diag.log.171025', u'collect db2pd and db2 snapshot success!']
    return jsonify(result='\n'.join(collect_result["stdout_lines"]))


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

    was_collect_cmd = "python collect_jc.py {0} {1}".format(prf_name, srv_name)
    app.logger.debug(was_collect_cmd)
    collect_result = {}
    if PRODUCT:
        collect_result = ansible_collect(inventory_in=was_inven, collect_cmd_str=was_collect_cmd)
    else:
        collect_result["stdout_lines"] = ["test1", "test2"]
    return jsonify(result='\n'.join(collect_result["stdout_lines"]))


if __name__ == '__main__':
    app.debug = True
    init_log()
    if PRODUCT:
        import sys
        reload(sys)
        sys.setdefaultencoding('utf8')
    app.run(host='0.0.0.0')
