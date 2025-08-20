
# condor_core/views.py

from django.shortcuts import render


def swagger_ui_view(request):
    """Render the Swagger UI documentation page.

    Args:
        request (HttpRequest): Incoming HTTP request.

    Returns:
        HttpResponse: Response containing the Swagger UI HTML.
    """
    return render(request, 'swagger.html')
