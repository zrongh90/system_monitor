import xlrd
from modules import System, WebSphere, DB2, db


def parse_file(in_file_path):
    file = xlrd.open_workbook(in_file_path)
    sheet = file.sheet_by_index(0)
    system_list = []
    for cur_row in range(1, sheet.nrows):
        fs = [sheet.cell_value(cur_row, x) for x in [0, 1, 2, 5, 6, 7, 8, 9]]
        one_system = System(inventory=fs[0], hostname=fs[1], os_info=fs[2], platform=fs[3], cpu_num=fs[4])
        system_list.append(one_system)
    return system_list


def main_parse():
    file_path = u'hostinfo_rhel_1709141108.xls'
    return parse_file(file_path)


if __name__ == '__main__':
    system_list = main_parse()
    #from db_utils import DBSession
    one_was = WebSphere(max_mem=2048, curr_mem=1024, prf_name="profile2", srv_name="server2", sys_inventory="10.8.5.34")
    two_was = WebSphere(max_mem=2048, curr_mem=1024, prf_name="profile1", srv_name="server1", sys_inventory="192.168.2.69")
    three_was = WebSphere(max_mem=2048, curr_mem=1014, prf_name="profile3", srv_name="server3", sys_inventory="10.8.5.34")

    one_db2 = DB2(sys_inventory="11.8.8.220", inst_name="test_inst", db_name="test_db", listen_port=50002)
    #session = DBSession()
    #db.session.add(three_was)
    db.session.add(one_db2)
    #db.session.add_all(system_list)
    #db.session.add(one_was)
    #db.session.add(two_was)
    #systems = session.query(System).all()
    #print(systems)
    #was = session.query(WebSphere).all()
    #print(was)
    db.session.commit()
    db.session.close()