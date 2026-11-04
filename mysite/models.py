from django.db import models


# 1. 设计一个数据库实例管理系统，用于管理企业内部的数据库实例，包含实例、集群、部门等模型
class DBInstance(models.Model):
    ENGINE_CHOICES = [
        ('mysql', 'MySQL'),
        ('redis', 'Redis'),
        ('mongodb', 'MongoDB'),
    ]
    ENV_CHOICES = [
        ('prod', '生产'),
        ('test', '测试'),
        ('dev', '开发'),
    ]
    ROLE_CHOICES = [
        ('primary', '主'),
        ('replica', '从'),
        ('standalone', '单机'),
    ]
    STATUS_CHOICES = [
        ('running', '运行中'),
        ('maintenance', '维护中'),
        ('degraded', '异常'),
        ('offline', '已下线'),
    ]

    # 实例基本信息
    name = models.CharField(max_length=100, unique=True)
    engine = models.CharField(max_length=20, choices=ENGINE_CHOICES)
    engine_version = models.CharField(max_length=30)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='standalone')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    environment = models.CharField(max_length=10, choices=ENV_CHOICES)

    # 连接信息
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField()
    db_name = models.CharField(max_length=100)
    db_secret = models.CharField(max_length=255)

    # 规格
    cpu_cores = models.PositiveIntegerField(null=True, blank=True)
    memory_mb = models.PositiveIntegerField(null=True, blank=True)
    storage_gb = models.PositiveIntegerField(null=True, blank=True)

    # 集群信息
    cluster_name = models.CharField(max_length=100)
    cluster_type = models.CharField(max_length=30, blank=True)

    # 部门与负责人
    department = models.CharField(max_length=100)                # 归属部门名
    owner = models.CharField(max_length=50)                      # 负责人姓名
    owner_phone = models.CharField(max_length=30, blank=True)    # 负责人电话

    # 生命周期
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    offline_at = models.DateTimeField(null=True, blank=True)
    remark = models.TextField(blank=True)

    class Meta:
        db_table = 'db_instance'
        constraints = [
            models.UniqueConstraint(fields=['host', 'port'], name='uniq_host_port'),
        ]
        indexes = [
            models.Index(fields=['engine', 'environment', 'status']),
            models.Index(fields=['department']),
        ]


class DBInstanceStatistics(models.Model):
    # 集群信息
    cluster_name = models.CharField(max_length=100)

    # 部门与负责人
    department = models.CharField(max_length=100)

    # 数量
    num = models.BigIntegerField()

    # 生命周期
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'db_instance_statistics'


