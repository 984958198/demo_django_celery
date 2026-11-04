
Django示例框架

如何测试运行：
    1.安装python（python3.8）

    2.安装该框架所有库requirements.txt内容

    3.命令行下执行：python manage.py runserver --settings=mysite.settings

    4.启动celery：
        celery -A mysite worker --loglevel=info --pool=solo

        celery -A mysite beat --loglevel=info
