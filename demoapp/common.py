from demoapp.models import Employee
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64


def get_owners(owners_json):
    """把 owners_json 解析成 InstanceOwner 对象列表并校验"""
    owners = set()
    for item in owners_json:
        emp_no = item.get("emp_no")
        role = item.get("owner_role")
        if not emp_no or not role:
            raise ValueError("owners 每项必须包含 employee_id 和 owner_role")
        try:
            emp = Employee.objects.get(pk=emp_no, is_active=True)
        except Employee.DoesNotExist:
            raise ValueError(f"员工 {emp_no} 不存在或已离职")
        key = {'employee': emp.id, 'owner_role': role}
        if key in owners:
            raise ValueError("同一负责人角色重复")
        owners.add(key)
    return list(owners)


def aes_encrypt_cbc(plaintext: str, key: bytes) -> str:
    iv = get_random_bytes(AES.block_size)
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