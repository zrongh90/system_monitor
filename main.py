# -*- coding: UTF-8 -*-
from flask import render_template, request, jsonify, url_for, flash
from sqlalchemy import distinct
from werkzeug.utils import redirect
from time import sleep

# from ansible_modules import ansible_collect
from modules import System, WebSphere, DB2, app, db

# from ansible_modules import ansible_run
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
    # print("get_all_system")
    page = request.args.get('page', 1, type=int)
    # 对结果进行分页
    paginate = System.query.paginate(page, NUM_PER_PAGE)
    systems = paginate.items
    # print(systems)
    for one_system in systems:
        sys_was_count = WebSphere.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_db2_count = DB2.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_was_count_list.append(sys_was_count)
        sys_db2_count_list.append(sys_db2_count)
    db.session.close()

    return render_template("all_system.html", inventory_filter_val="", title="主机信息列表", system_list=systems,
                           pagination=paginate, os_filter_val="", os_list_val=get_os_list(),
                           sys_was_count_list=sys_was_count_list, sys_db2_count_list=sys_db2_count_list)


# 获取过滤后的系统信息，可以根据（inventory/os)进行过滤
# input: inventory_filter:IP过滤器
#        os_filter: 操作系统类型过滤器
# return: details.html
@app.route('/filter', methods=['POST', 'GET'])
def get_filter_system(inventory_filter=None, os_filter=None):
    print("filter")
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


# 传统的获取系统信息的方法，根据系统的inventory获取系统信息，was信息和db2信息并渲染details.html返回
# input: inventory
# return: details.html
@app.route('/detail/<inventory>')
def detail(inventory=None):
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
        print(new_db2_detail)
        return render_template("details.html", title="具体信息", system_detail_in=system_detail,
                               was_detail_in=new_was_detail,
                               db2_detail_in=new_db2_detail)
    except Exception as e:
        my_log(e)
        # 更新失败，立刻回滚
        db.session.rollback()
        # TODO: 使用flash进行提示
        return render_template("500.html")


@app.route('/tivoli')
def tivoli():
    return render_template("tivoli.html")


@app.route('/clear_tivoli_alert', methods=['POST'])
def clear_tivoli_alert():
    my_log("test_clear")
    event_id = request.form.get('event_id', 0, type=int)
    event_ip = request.form.get('event_ip', 0, type=str)
    event_content = request.form.get('event_content', 0, type=str)

    my_log(event_id)
    msg = "success update tivoli for event_id: " + str(event_id)
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
    inventory_input = request.args.get('invent_val', 0, type=str)
    my_log("inventory_input:" + inventory_input)
    db2_detail = DB2.query.filter_by(sys_inventory=inventory_input)
    return jsonify(result=[i.serialize for i in db2_detail.all()])


# 通过jquery获取收集DB2信息
# input: db_inven 收集DB2日志的系统IP
# input: db_name  收集的数据库
# input: inst_name 数据库的instance用户名
# return: serialized DB2 Object
@app.route('/_collect_db2')
def jquery_collect_db2():
    db_inven = request.args.get('db_inven', 0, type=str)
    db_name = request.args.get('db_name', 0, type=str)
    inst_name = request.args.get('inst_name', 0, type=str)
    db2_collect_cmd_str = "su - " + inst_name + " -c \"/zxyx/collect/get_db2_log.sh " + inst_name \
                          + " \'\' " + db_name + "\""
    my_log(db2_collect_cmd_str)
    # TODO: call ansible to run command to collect db2 snapshot and pd
    # ansible_collect(db_inven, db2_collect_cmd_str)
    # return jsonify(result=[i.serialize for i in db2_detail.all()])
    sleep(2)
    return jsonify(result="test")


# 通过jquery获取收集websphere信息
@app.route('/_collect_was')
def jquery_collect_was():
    was_inven = request.args.get('was_inven', 0, type=str)
    prf_name = request.args.get('prf_name', 0, type=str)
    srv_name = request.args.get('srv_name', 0, type=str)
    my_log(was_inven + ' ' + prf_name + ' ' + srv_name)
    sleep(5)
    return jsonify(result="success")


if __name__ == '__main__':
    app.debug = True
    # import sys
    # reload(sys)
    # sys.setdefaultencoding('utf8')
    app.run(host='0.0.0.0')
