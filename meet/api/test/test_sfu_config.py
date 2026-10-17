from unittest import TestCase
from unittest.mock import patch

from meet.utils.sfu_config import _build_sfu_presence_url, get_sfu_presence_url


class TestSFUPresenceURL(TestCase):
	def test_uses_internal_server_url_and_configured_port(self):
		self.assertEqual(
			_build_sfu_presence_url("http://171.244.63.182", 4000),
			"http://171.244.63.182:4000/internal/presence",
		)

	def test_preserves_explicit_port_and_path_prefix(self):
		self.assertEqual(
			_build_sfu_presence_url("https://meet.nextgrp.vn/sfu", 4000),
			"https://meet.nextgrp.vn/sfu/internal/presence",
		)

	@patch("meet.utils.sfu_config.frappe")
	def test_presence_url_prefers_canonical_sfu_settings(self, frappe_mock):
		settings = {
			"sfu_server_url": "http://sfu-internal",
			"sfu_server_port": 3000,
			"meet_server_url": "http://legacy-meet",
			"meet_server_port": 8000,
		}
		frappe_mock.conf.get.side_effect = lambda key, default=None: settings.get(key, default)

		self.assertEqual(get_sfu_presence_url(), "http://sfu-internal:3000/internal/presence")

	@patch("meet.utils.sfu_config.frappe")
	def test_presence_url_falls_back_to_legacy_meet_settings(self, frappe_mock):
		settings = {"meet_server_url": "http://legacy-sfu", "meet_server_port": 3001}
		frappe_mock.conf.get.side_effect = lambda key, default=None: settings.get(key, default)

		self.assertEqual(get_sfu_presence_url(), "http://legacy-sfu:3001/internal/presence")
