"""
Converts legal document markdown files to pre-rendered HTML.

Walks assets/legal/ for all *.md files and writes a sibling .html file
for each one. The generated HTML is body-fragment only (no <html>/<head>
wrappers) so it can be served directly via the API and injected with v-html.
"""

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
        legal_dir = settings.ASSETS_ROOT / 'legal'

        if not legal_dir.exists():
            self.stderr.write(self.style.ERROR(f'Legal assets directory not found: {legal_dir}'))
            return

        md = markdown.Markdown(extensions=['tables'])
        md_files = sorted(legal_dir.rglob('*.md'))

        if not md_files:
            self.stdout.write(self.style.WARNING('No markdown files found.'))
            return

        for md_file in md_files:
            html_file = md_file.with_suffix('.html')
            md.reset()
            source = md_file.read_text(encoding='utf-8')
            html = md.convert(source)
            html_file.write_text(html + '\n', encoding='utf-8')

            rel_path = md_file.relative_to(settings.ASSETS_ROOT)
            self.stdout.write(self.style.SUCCESS(f'Converted {rel_path} -> {html_file.name}'))
