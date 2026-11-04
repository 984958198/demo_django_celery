import time

from django.views import View
from mysite.models import DBInstance
import json, socket


# 2. 提供对应模型的增删改查接口；
class InstanceView(View):
    """数据库实例增删改查接口"""

    def get(self, request):
        return self.post(request)

    def post(self, request):
        params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
        page, pagesize = int(params.get('page') or 1), int(params.get('pagesize', 10))
        obj = DBInstance.objects.filter(**params.get('filters', {}))
        data = {'total': obj.count(), 'data': obj[page * pagesize - pagesize: page * pagesize]}
        return data

    def put(self, request):
        params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
        # 整理键和值就不写了
        obj = DBInstance.objects.create(**params)
        return obj

    def patch(self, request):
        params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
        obj = DBInstance.objects.filter(id=params.pop('id')).update(**params)
        return obj

    def delete(self, request):
        params = dict(dict(request.GET.dict(), **request.POST.dict()), **json.loads(request.body or '{}'))
        obj = DBInstance.objects.filter(**params).delete()
        return obj


# 2. 提供一个 API，用于探测某个实例是否 TCP 端口可达
def tcp(request):
    host = request.GET['host']
    port = request.GET['port']
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=3):
            elapsed = round((time.monotonic() - start) * 1000, 2)
            return {'host': host, 'port': port, 'reachable': True, 'latency_ms': elapsed, 'error': None}
    except Exception as e:
        elapsed = round((time.monotonic() - start) * 1000, 2)
        return {'host': host, 'port': port, 'reachable': False, 'latency_ms': elapsed, 'error': str(e)}

