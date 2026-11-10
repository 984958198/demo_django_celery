from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Department(models.Model):
    """部门，支持树形组织"""
    dept_code = models.CharField("部门编码", max_length=32, unique=True)
    dept_name = models.CharField("部门名称", max_length=128)
    parent = models.ForeignKey(
        "self", verbose_name="上级部门", null=True, blank=True,
        on_delete=models.PROTECT, related_name="children"
    )
    dept_path = models.CharField("组织路径", max_length=512, blank=True, db_index=True)
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "department"
        verbose_name = "部门"
        verbose_name_plural = verbose_name
        ordering = ["dept_code"]

    def save(self, *args, **kwargs):
        # 维护 dept_path，便于子树查询
        if self.parent:
            self.dept_path = f"{self.parent.dept_path}/{self.dept_name}"
        else:
            self.dept_path = f"{self.dept_name}"
        super().save(*args, **kwargs)


class Employee(models.Model):
    """人员，用于实例负责人"""
    emp_no = models.CharField("工号", max_length=32, unique=True)
    emp_name = models.CharField("姓名", max_length=64)
    department = models.ForeignKey(
        Department, verbose_name="所属部门", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="employees"
    )
    email = models.EmailField("邮箱", blank=True)
    is_active = models.BooleanField("在职", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "employee"
        verbose_name = "人员"
        verbose_name_plural = verbose_name


class DBCluster(models.Model):
    """数据库集群"""
    class DBType(models.TextChoices):
        MYSQL = "mysql", "MySQL"
        REDIS = "redis", "Redis"
        MONGODB = "mongodb", "MongoDB"
        OTHER = "other", "其他"

    class DeployMode(models.TextChoices):
        STANDALONE = "standalone", "单机"
        MASTER_SLAVE = "master_slave", "主从"
        MASTER_STANDBY = "master_standby", "主备"

    class Env(models.TextChoices):
        PROD = "prod", "生产"
        STAGING = "staging", "预发"
        DEV = "dev", "开发"
        TEST = "test", "测试"

    class Status(models.TextChoices):
        RUNNING = "running", "运行中"
        MAINTENANCE = "maintenance", "维护中"
        OFFLINE = "offline", "已下线"

    cluster_code = models.CharField("集群编码", max_length=64, unique=True)
    cluster_name = models.CharField("集群名称", max_length=128)
    db_type = models.CharField("数据库类型", max_length=32, choices=DBType.choices)
    deploy_mode = models.CharField("部署模式", max_length=32, choices=DeployMode.choices)
    version = models.CharField("版本", max_length=32, blank=True)
    env = models.CharField("环境", max_length=16, choices=Env.choices)
    region = models.CharField("机房/可用区", max_length=64, blank=True)
    status = models.CharField("状态", max_length=16, choices=Status.choices, default=Status.RUNNING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "db_cluster"
        verbose_name = "数据库集群"
        verbose_name_plural = verbose_name
        ordering = ["cluster_code"]


class DBInstance(models.Model):
    """数据库实例"""
    class Role(models.TextChoices):
        PRIMARY = "primary", "主"
        REPLICA = "replica", "从"
        STANDBY = "standby", "备"
        STANDALONE = "standalone", "单机"

    class Status(models.TextChoices):
        RUNNING = "running", "运行中"
        STOPPED = "stopped", "已停止"
        MAINTENANCE = "maintenance", "维护中"
        OFFLINE = "offline", "已下线"

    instance_code = models.CharField("实例编码", max_length=64, unique=True)
    instance_name = models.CharField("实例名称", max_length=128)
    cluster = models.ForeignKey(
        DBCluster, verbose_name="所属集群", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="instances"
    )
    owner_dept = models.ForeignKey(
        Department, verbose_name="归属部门", on_delete=models.PROTECT,
        related_name="owned_instances"
    )
    db_type = models.CharField("数据库类型", max_length=32, choices=DBCluster.DBType.choices)
    db_version = models.CharField("版本", max_length=32, blank=True)
    env = models.CharField("环境", max_length=16, choices=DBCluster.Env.choices)
    host = models.GenericIPAddressField("主机IP")
    port = models.PositiveIntegerField("端口", validators=[MinValueValidator(1), MaxValueValidator(65535)])
    password_cipher = models.CharField("加密密码", max_length=256, blank=True)  # 不考虑不同账号不同密码情况
    role = models.CharField("角色", max_length=16, choices=Role.choices, blank=True)
    status = models.CharField("状态", max_length=16, choices=Status.choices, default=Status.RUNNING)
    conn_spec = models.CharField("连接规格描述", max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "db_instance"
        verbose_name = "数据库实例"
        verbose_name_plural = verbose_name
        ordering = ["instance_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["host_ip", "port"],
                name="uk_instance_host_port",
            )
        ]
        indexes = [
            models.Index(fields=["owner_dept", "env"]),
            models.Index(fields=["cluster", "status"]),
        ]

    def save(self, *args, **kwargs):
        # 独立实例（不挂集群）时，从集群同步 db_type/env 的可选兜底
        if self.cluster_id:
            if not self.db_type:
                self.db_type = self.cluster.db_type
            if not self.env:
                self.env = self.cluster.env
        super().save(*args, **kwargs)


class InstanceOwner(models.Model):
    """实例负责人"""
    class OwnerRole(models.TextChoices):
        DBA = "dba", "DBA"
        APP_OWNER = "app_owner", "应用负责人"
        BACKUP_DBA = "backup_dba", "备份DBA"

    instance = models.ForeignKey(
        DBInstance, verbose_name="实例", on_delete=models.CASCADE,
        related_name="owners"
    )
    employee = models.ForeignKey(
        Employee, verbose_name="负责人", on_delete=models.CASCADE,
        related_name="owned_instances"
    )
    owner_role = models.CharField(
        "负责角色", max_length=32, choices=OwnerRole.choices
    )

    class Meta:
        db_table = "instance_owner"
        verbose_name = "实例负责人"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["instance", "employee", "owner_role"],
                name="uk_instance_emp_role",
            )
        ]


class InstanceChangeLog(models.Model):
    """实例变更留痕"""
    class ChangeType(models.TextChoices):
        CREATE = "create", "创建"
        MODIFY = "modify", "修改"
        OFFLINE = "offline", "下线"

    instance = models.ForeignKey(
        DBInstance, verbose_name="实例", on_delete=models.CASCADE,
        related_name="change_logs"
    )
    change_type = models.CharField("变更类型", max_length=32, choices=ChangeType.choices)
    old_value = models.TextField("旧值", blank=True)
    new_value = models.TextField("新值", blank=True)
    operator = models.ForeignKey(
        Employee, verbose_name="操作人", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="change_logs"
    )
    operated_at = models.DateTimeField("操作时间", auto_now_add=True)
    remark = models.CharField("备注", max_length=512, blank=True)

    class Meta:
        db_table = "instance_change_log"
        verbose_name = "实例变更记录"
        verbose_name_plural = verbose_name
        ordering = ["-operated_at"]


class DBInstanceStats(models.Model):
    cluster = models.ForeignKey(
        DBCluster, verbose_name="所属集群", null=True, blank=True,
        on_delete=models.CASCADE, related_name="instance_stats"
    )
    owner_dept = models.ForeignKey(
        Department, verbose_name="归属部门", on_delete=models.CASCADE,
        related_name="instance_stats"
    )
    num = models.BigIntegerField('实例数量')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'db_instance_stats'
        verbose_name = "实例统计按集群和部门"
        verbose_name_plural = verbose_name
