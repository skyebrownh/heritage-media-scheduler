from django.http import HttpResponse


def health(request):
    """Railway's health check. The one page without a login, so it must never show data.

    It deliberately touches no database: it answers "is the process up", nothing more.
    """
    return HttpResponse("ok", content_type="text/plain")
