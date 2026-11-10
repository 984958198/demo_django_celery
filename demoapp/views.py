import time

from django.views import View
from demoapp.models import DBInstance, Department, InstanceOwner, InstanceChangeLog
import json
import socket
from django.db import transaction
from demoapp.common import get_owners

# 2. 提供对应模型的增删改查接口；
class InstanceView(View):
    """数据库实例增删改查接口"""

    def get(self, request):
        # 查询
        return self.post(request)

    def post(self, request):
        # 查询
        params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
        page, pagesize = int(params.get('page') or 1), int(params.get('pagesize', 10))
        obj = DBInstance.objects.filter(**params.get('filters', {}))
        data = {'total': obj.count(), 'data': obj[page * pagesize - pagesize: page * pagesize]}
        return data

    def put(self, request):
        # 创建
        params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
        # 整理键和值就不写了
        # 操作人
        params['operator'] = request.user['id']
        # 获取归属部门
        dept = Department.objects.filter(pk=params.pop('dept_code'), is_active=True).first()
        assert dept, (f"部门不存在", 404)  # 抛出异常元组可由中间件统一处理状态码
        params['owner_dept'] = dept.id
        # 解析实例负责人
        owners = get_owners(params.pop('owners', []))
        with transaction.atomic():
            instance = DBInstance.objects.create(**params)
            new_value = json.dumps(dict(instance.to_dict(), **{'owners': owners}))
            InstanceChangeLog.objects.create(instance=instance.id, change_type='create', new_value=new_value, operator=params['operator'])
            if owners:
                InstanceOwner.objects.bulk_create([InstanceOwner(instance=instance.id, **o) for o in owners])
        return instance

    def patch(self, request):
        # 修改
        params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
        instance = DBInstance.objects.filter(pk=params.pop('id')).first()
        assert instance, (f"实例不存在", 404)
        # 操作人
        params['operator'] = request.user['id']
        # 修改归属部门
        if params.get('dept_code'):
            dept = Department.objects.filter(pk=params.pop('dept_code'), is_active=True).first()
            assert dept, f"部门不存在"
            params['owner_dept'] = dept.id
        # 解析实例负责人
        owners = get_owners(params.pop('owners', []))
        old_owners = InstanceOwner.objects.filter(instance=instance.id)
        old_value = json.dumps(dict(instance.to_dict(), **{'owners': old_owners}))
        with transaction.atomic():
            new_instance = instance.update(**params)
            new_value = json.dumps(dict(new_instance.to_dict(), **{'owners': owners}))
            InstanceChangeLog.objects.create(instance=new_instance.id, change_type='update', old_value=old_value, new_value=new_value, operator=params['operator'])
            if owners:
                InstanceOwner.objects.bulk_create([InstanceOwner(instance=new_instance.id, **o) for o in owners])
        return instance

    def delete(self, request):
        # 删除（伪删除）
        params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
        instance = DBInstance.objects.filter(pk=params.pop('id')).first()
        assert instance, (f"实例不存在", 404)
        # 操作人
        params['operator'] = request.user['id']
        with transaction.atomic():
            instance.status = 'offline'
            InstanceChangeLog.objects.create(instance=instance.id, change_type='offline', operator=params['operator'])
        return instance
        obj = DBInstance.objects.filter(**params).delete()
        return obj


# 2. 提供一个 API，用于探测某个实例是否 TCP 端口可达
def tcp(request):
    params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
    host = params.get('host')
    port = params.get('port')
    if not host or not port:
        instance = DBInstance.objects.filter(pk=params.pop('id')).first()
        assert instance, (f"实例不存在", 404)
        host = instance.host
        port = instance.port
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=3):
            elapsed = round((time.monotonic() - start) * 1000, 2)
            return {'host': host, 'port': port, 'reachable': True, 'latency_ms': elapsed, 'error': None}
    except Exception as e:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        return {'host': host, 'port': port, 'reachable': False, 'latency_ms': elapsed, 'error': str(e)}

