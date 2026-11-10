from django.utils.deprecation import MiddlewareMixin
from django.http.response import JsonResponse, HttpResponse, StreamingHttpResponse
from functools import wraps
import logging
import time
from proj.celery import app as celery_app


class ViewsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 视图函数前被调用
        request._start_time = time.monotonic()

    def process_response(self, request, response):
        # 视图函数返回时调用
        start = getattr(request, '_start_time', None)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2) if start else -1
        # 5. 实现一个中间件，统计每个请求的请求耗时
        logging.info(f'API耗时 {request.method} {request.path} -> {elapsed_ms}ms')
        if isinstance(response, (JsonResponse, HttpResponse, StreamingHttpResponse)):
            return response
        else:
            return JsonResponse({'code': 0, 'data': response, 'message': ''})

    def process_exception(self, request, exception):
        # 视图函数发生异常时调用
        logging.exception(exception)
        code = exception.args[1] if isinstance(exception.args, tuple) else 1
        return JsonResponse({'code': code, 'message': exception})


def login_exempt(view_func):
    # 免登入装饰器，在中间件中已默认所有接口登入
    def wrapped_view(*args, **kwargs):
        return view_func(*args, **kwargs)

    wrapped_view.login_exempt = True
    return wraps(view_func)(wrapped_view)


