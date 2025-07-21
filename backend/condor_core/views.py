
# condor_core/views.py

from django.shortcuts import render

def swagger_ui_view(request):
    return render(request, 'swagger.html')
