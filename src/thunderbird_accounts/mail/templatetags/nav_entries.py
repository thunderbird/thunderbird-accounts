from django import template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.simple_tag
def mail_nav_entries(current_page):
    """Returns a list of dict containing the path, human name, and if the page is selected."""
    return [
        {
            'path': reverse('self_serve_connection_info'),
            'name': _('Connection Info'),
            'selected': reverse('self_serve_connection_info') == current_page,
        },
        {
            'path': reverse('self_serve_app_password'),
            'name': _('App Password'),
            'selected': reverse('self_serve_app_password') == current_page,
        },
    ]
