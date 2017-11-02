import modules
import ansible_modules
import utils

sys_list = modules.System.query.all()
for sys in sys_list:
    detail_host_ok = ansible_modules.details_ansible_run(inventory_in=sys.inventory)
    utils.detail_update(sys, detail_host_ok)
    modules.db.session.commit()
