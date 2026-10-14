import pytest

from live_images import parse_live_ref, resolve_live_images

LIVE_KEYCLOAK = 'live:accounts-stage-fargate-keycloak/accounts-stage-fargate-keycloak/keycloak'
LIVE_ACCOUNTS = 'live:accounts-stage-fargate-accounts/accounts-stage-fargate-accounts/accounts'


def fake_lookup(calls):
    def lookup(cluster, service, container):
        calls.append((cluster, service, container))
        return f'ecr/{container}:running'

    return lookup


def test_parse_live_ref():
    assert parse_live_ref(LIVE_KEYCLOAK) == (
        'accounts-stage-fargate-keycloak',
        'accounts-stage-fargate-keycloak',
        'keycloak',
    )


@pytest.mark.parametrize('value', ['live:', 'live:cluster/service', 'live:cluster//container', 'live:a/b/c/d'])
def test_parse_live_ref_rejects_malformed(value):
    with pytest.raises(ValueError, match='expected live:<cluster>/<service>/<container>'):
        parse_live_ref(value)


def test_resolves_nested_references_in_place():
    config = {
        'tb:fargate:FargateClusterWithLogging': {
            'keycloak': {'task_definition': {'container_definitions': {'keycloak': {'image': LIVE_KEYCLOAK}}}},
        },
        'tb:fargate:AutoscalingFargateCluster': {
            'celery': {'container_definitions': [{'image': LIVE_ACCOUNTS}, {'image': LIVE_ACCOUNTS}]},
        },
    }
    calls = []

    result = resolve_live_images(config, fake_lookup(calls))

    assert result is config
    kc = config['tb:fargate:FargateClusterWithLogging']['keycloak']['task_definition']['container_definitions']
    assert kc['keycloak']['image'] == 'ecr/keycloak:running'
    celery = config['tb:fargate:AutoscalingFargateCluster']['celery']['container_definitions']
    assert [c['image'] for c in celery] == ['ecr/accounts:running', 'ecr/accounts:running']
    # The shared accounts reference is looked up once.
    assert sorted(calls) == sorted(
        [
            ('accounts-stage-fargate-keycloak', 'accounts-stage-fargate-keycloak', 'keycloak'),
            ('accounts-stage-fargate-accounts', 'accounts-stage-fargate-accounts', 'accounts'),
        ]
    )


def test_leaves_explicit_images_and_other_values_alone():
    config = {'image': 'ecr/accounts:keycloak-abc123', 'desired_count': 1, 'assign_public_ip': True, 'name': None}
    calls = []

    resolve_live_images(config, fake_lookup(calls))

    assert config == {
        'image': 'ecr/accounts:keycloak-abc123',
        'desired_count': 1,
        'assign_public_ip': True,
        'name': None,
    }
    assert calls == []


def test_lookup_errors_propagate():
    def failing_lookup(cluster, service, container):
        raise RuntimeError('service not found')

    with pytest.raises(RuntimeError, match='service not found'):
        resolve_live_images({'image': LIVE_KEYCLOAK}, failing_lookup)
