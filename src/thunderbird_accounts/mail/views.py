from django.http import HttpRequest
from django.shortcuts import render
from django.template.response import TemplateResponse


# Create your views here.


def home(request: HttpRequest):
    return TemplateResponse(request, 'mail/index.html', {})


def self_serve(request: HttpRequest):
    return TemplateResponse(request, 'mail/self-serve.html', {})


def signup(request: HttpRequest):
    return TemplateResponse(request, 'mail/signup.html', {})
