"""Resolve ``live:`` image references in the stack config.

Stage doesn't commit image tags. merge.yml overrides the image anchors with the images it just
built; every other image in the config is written as ``live:<cluster>/<service>/<container>``
and resolves to whatever that ECS service is running now. That way a `pulumi up` outside CI
reproduces what's deployed instead of rolling back to a stale committed tag (#1409).
"""

LIVE_PREFIX = 'live:'


def parse_live_ref(value: str) -> tuple[str, str, str]:
    parts = value[len(LIVE_PREFIX) :].split('/')
    if len(parts) != 3 or not all(parts):
        raise ValueError(f'Invalid live image reference "{value}"; expected live:<cluster>/<service>/<container>')
    return parts[0], parts[1], parts[2]


def resolve_live_images(node, lookup, cache: dict | None = None):
    """Replace every ``live:`` string in ``node`` with ``lookup(cluster, service, container)``.

    Dicts and lists are updated in place; the resolved node is also returned. Each distinct
    reference is looked up once.
    """
    if cache is None:
        cache = {}

    if isinstance(node, str):
        if not node.startswith(LIVE_PREFIX):
            return node
        if node not in cache:
            cache[node] = lookup(*parse_live_ref(node))
        return cache[node]

    if isinstance(node, dict):
        for key, value in node.items():
            node[key] = resolve_live_images(value, lookup, cache)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            node[i] = resolve_live_images(value, lookup, cache)

    return node
