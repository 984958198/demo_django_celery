from django.conf import settings
from celery import shared_task
from mysite.models import DBInstance, DBInstanceStatistics
import secrets
import string
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64
from django.db.models import Count


def aes_encrypt_cbc(plaintext: str, key: bytes) -> str:
    iv = get_random_bytes(AES.block_size)  # 16 字节随机 IV
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(iv + encrypted).decode()


def aes_decrypt_cbc(ciphertext_b64: str, key: bytes) -> str:
    raw = base64.b64decode(ciphertext_b64)
    iv, encrypted = raw[:AES.block_size], raw[AES.block_size:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted)
    return unpad(decrypted, AES.block_size).decode('utf-8')


# 3. 需维护每个实例的账号密码，每隔 12 小时随机轮换每个实例的密码并加密记录
@shared_task
def update_secret_instances():
    key = getattr(settings, 'AES_KEY', b'0123456789abcdef')
    for d in DBInstance.objects.all():
        password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(16))
        if update_password(d.host, d.port, d.password):
            d.db_secret = aes_encrypt_cbc(password, key)
            try:
                d.save()
            except Exception as e:
                logging.error(f'保存数据库失败，请手动执行{d.host}:{d.port}->{d.db_secret}')
        else:
            logging.error(f'更换失败{d.host}:{d.port}')


def update_password(host, port, password) -> bool:
    # 更换实例密码
    return True


# 4. 每天 00:00 按部门和集群维度统计实例数量，并把统计数据写入数据库
@shared_task
def statistics_instances():
    rows = DBInstance.objects.values('cluster_name', 'department').annotate(num=Count('id'))
    objs = [DBInstanceStatistics(**r) for r in rows]
    DBInstanceStatistics.objects.bulk_create(objs)
