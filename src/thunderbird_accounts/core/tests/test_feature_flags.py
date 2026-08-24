import ast
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class FeatureFlagDocumentationSyncTestCase(SimpleTestCase):
    """Keep the canonical feature flag inventory in sync with the code."""

    def test_documented_feature_flags_match_code(self):
        self.assertSetEqual(self._extract_code_feature_flags(), self._extract_documented_feature_flags())

    @staticmethod
    def _extract_code_feature_flags() -> set[str]:
        base_dir = Path(settings.BASE_DIR)
        vue_types = (base_dir / 'assets' / 'app' / 'vue' / 'types.ts').read_text()
        enum_match = re.search(r'export enum WAFFLE_FLAG\s*{(?P<body>.*?)}', vue_types, re.DOTALL)
        if not enum_match:
            raise AssertionError('Could not find the frontend WAFFLE_FLAG enum')

        feature_flags = set(re.findall(r"=\s*'([^']+)'", enum_match.group('body')))

        for python_file in (base_dir / 'src' / 'thunderbird_accounts').rglob('*.py'):
            module = ast.parse(python_file.read_text(), filename=str(python_file))
            for node in ast.walk(module):
                if isinstance(node, ast.Assign):
                    targets = node.targets
                    value = node.value
                elif isinstance(node, ast.AnnAssign):
                    targets = [node.target]
                    value = node.value
                else:
                    continue

                if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                    continue

                for target in targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id.startswith('WAFFLE_FLAG_') or target.id.endswith(('_FLAG', '_SWITCH')):
                        feature_flags.add(value.value)

        return feature_flags

    @staticmethod
    def _extract_documented_feature_flags() -> set[str]:
        documentation = (Path(settings.BASE_DIR) / 'docs' / 'feature-flags.rst').read_text()
        return set(re.findall(r'^\s+\* - ``([^`]+)``$', documentation, re.MULTILINE))
