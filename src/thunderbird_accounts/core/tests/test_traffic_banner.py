from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from waffle.testutils import override_switch


class IncreasedTrafficBannerSwitchTestCase(TestCase):
    """The frontend's TrafficBanner component reads switch state from the wafflejs endpoint
    (window.waffle.switch_is_active), so make sure the increased-traffic-banner switch is
    reported correctly when toggled on and off."""

    def setUp(self):
        self.url = reverse('wafflejs')

    @override_switch(settings.WAFFLE_SWITCH_INCREASED_TRAFFIC_BANNER, active=True)
    def test_switch_reported_active(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f"'{settings.WAFFLE_SWITCH_INCREASED_TRAFFIC_BANNER}': true", content)

    @override_switch(settings.WAFFLE_SWITCH_INCREASED_TRAFFIC_BANNER, active=False)
    def test_switch_reported_inactive(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f"'{settings.WAFFLE_SWITCH_INCREASED_TRAFFIC_BANNER}': false", content)
