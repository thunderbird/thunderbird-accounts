from django.http import HttpRequest
from django.shortcuts import render
from django.template.response import TemplateResponse


# Create your views here.


def home(request: HttpRequest):
    return TemplateResponse(request, 'mail/index.html', {})


def self_serve(request: HttpRequest):
    return TemplateResponse(request, 'mail/self-serve.html', {})


def wait_list(request: HttpRequest):
    return TemplateResponse(request, 'mail/wait-list.html', {})
