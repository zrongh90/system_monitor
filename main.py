from flask import render_template, request, jsonify
from sqlalchemy import distinct

from modules import System, WebSphere, DB2, app, db
#from test_ansible import ansible_run
from ansible_modules import ansible_run
from utils import ansible_get

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
        print("POST")
    elif request.method == 'GET':
        inventory_filter = request.args.get('inventory_filter')
        os_filter = request.args.get('os_filter')
        print("GET")
    print("inventory_filter:" + inventory_filter)
    print("os_filter:" + os_filter)
    page = request.args.get('page', 1, type=int)
    # 对结果进行分页
    if os_filter == "all":
        paginate = System.query.filter(System.inventory.like(inventory_filter + "%")).paginate(page, NUM_PER_PAGE)
    else:
        paginate = System.query.filter(System.inventory.like(inventory_filter + "%")). \
            filter(System.os_info == str(os_filter)).paginate(page, NUM_PER_PAGE)
    systems = paginate.items
    for one_system in systems:
        sys_was_count = WebSphere.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_db2_count = DB2.query.filter_by(sys_inventory=one_system.inventory).count()
        sys_was_count_list.append(sys_was_count)
        sys_db2_count_list.append(sys_db2_count)
    db.session.close()
    print(systems)
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
        for one_was in was_detail:
            db.session.delete(one_was)
        # call ansible function to retrieve websphere,db2,system info for target inventory
        # current only realize get websphere info
        #ansible_run(inventory_in=inventory)
        db.session.commit()
        new_was_detail = WebSphere.query.filter_by(sys_inventory=inventory).all()
        return render_template("details.html", title="具体信息", system_detail_in=system_detail,
                               was_detail_in=new_was_detail,
                               db2_detail_in=db2_detail)
    except Exception as e:
        print(e.message)
        # 更新失败，立刻回滚
        db.session.rollback()
        # TODO: 使用flash进行提示
        return render_template("500.html")


# 通过jquery获取系统的WAS信息
# input: invent_val
# return: serialized WebSphere Object
@app.route('/_get_was')
def jquery_get_was_info():
    inventory_input = request.args.get('invent_val', 0, type=str)
    print("inventory_input:" + inventory_input)
    was_detail = WebSphere.query.filter_by(sys_inventory=inventory_input)
    return jsonify(result=[i.serialize for i in was_detail.all()])


# 通过jquery获取系统的DB2信息
# input: invent_val
# return: serialized DB2 Object
@app.route('/_get_db2')
def jquery_get_db2_info():
    inventory_input = request.args.get('invent_val', 0, type=str)
    print("inventory_input:" + inventory_input)
    db2_detail = DB2.query.filter_by(sys_inventory=inventory_input)
    return jsonify(result=[i.serialize for i in db2_detail.all()])


if __name__ == '__main__':
    app.debug = True
    app.run()
