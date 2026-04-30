"""
Converts legal document markdown files to pre-rendered HTML.

Walks assets/legal/ for all *.md files and writes a sibling .html file
for each one. The generated HTML is body-fragment only (no <html>/<head>
wrappers) so it can be served directly via the API and injected with v-html.
"""
from django.apps import apps
from pathlib import Path

import markdown
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Usage:

    .. code-block:: shell

        python manage.py convert_legal_docs

    """

    help = 'Converts legal document markdown files under assets/legal/ to HTML.'

    def handle(self, *args, **options):
        legal_app_path = apps.get_app_config("legal").path

        legal_dir_in = Path(settings.ASSETS_ROOT, 'legal')
        legal_dir_out = Path(legal_app_path, 'templates')   

        if not legal_dir_in.exists() or not legal_dir_out.exists():
            self.stderr.write(
                self.style.ERROR(f'Legal assets directory not found! In: {legal_dir_in} / Out: {legal_dir_out}')
            )
            return

        md = markdown.Markdown(extensions=['attr_list', 'tables'])
        md_files = sorted(legal_dir_in.rglob('*.md'))

        if not md_files:
            self.stdout.write(self.style.WARNING('No markdown files found.'))
            return

        for md_file in md_files:
            file_name = md_file.stem
            # Retrieve the last two folders (as of writing this it's 'privacy' -or- 'tos' and 'v1.0')
            type, version =  md_file.resolve().parent.parts[-2:]
            html_file = Path(legal_dir_out, type, version, f'{file_name}.html')
            md.reset()
            source = md_file.read_text(encoding='utf-8')
            html = md.convert(source)
            html_file.write_text(html + '\n', encoding='utf-8')

            rel_path = md_file.relative_to(settings.ASSETS_ROOT)
            self.stdout.write(self.style.SUCCESS(f'Converted {rel_path} -> {html_file.name}'))
