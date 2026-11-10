from django.conf import settings
from celery import shared_task
from demoapp.models import DBInstance, InstanceChangeLog, DBInstanceStatistics
import secrets
import string
import logging
from django.db.models import Count
from django.db import transaction
from demoapp.common import aes_encrypt_cbc


# 3. 需维护每个实例的账号密码，每隔 12 小时随机轮换每个实例的密码并加密记录
@shared_task
def update_password_instances():
    key = get_key()
    for instance in DBInstance.objects.filter(status__ne='offline').all():
        password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(16))
        if update_password(instance.host, instance.port, password):
            old_value = {'password_cipher': instance.password_cipher}
            instance.password_cipher = aes_encrypt_cbc(password, key)
            new_value = {'password_cipher': instance.password_cipher}
            try:
                with transaction.atomic():
                    instance.save()
                    InstanceChangeLog.objects.create(instance=instance.id, change_type='update', old_value=old_value, new_value=new_value, operator='task')
            except Exception as e:
                logging.error(f'保存数据库失败，请手动执行{instance.host}:{instance.port}->{instance.password_cipher}')
        else:
            logging.error(f'更换失败{instance.host}:{instance.port}')


def get_key() -> bytes:
    # 获取加密key
    return b'0123456789abcdef'


def update_password(host, port, password) -> bool:
    # 更换实例密码
    return True


# 4. 每天 00:00 按部门和集群维度统计实例数量，并把统计数据写入数据库
@shared_task
def statistics_instances():
    rows = DBInstance.objects.filter(status__ne='offline').values('cluster', 'owner_dept').annotate(num=Count('id'))
    objs = [DBInstanceStatistics(**r) for r in rows]
    DBInstanceStatistics.objects.bulk_create(objs)
