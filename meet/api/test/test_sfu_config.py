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

	@patch("meet.utils.sfu_config.get_sfu_config")
	@patch("meet.utils.sfu_config.frappe")
	def test_presence_url_prefers_internal_meet_endpoint(self, frappe_mock, get_sfu_config):
		settings = {
			"sfu_server_url": "https://meet.nextgrp.vn/sfu",
			"sfu_server_port": 3000,
			"meet_server_url": "http://171.244.63.182",
			"meet_server_port": 4000,
		}
		frappe_mock.conf.get.side_effect = lambda key, default=None: settings.get(key, default)
		get_sfu_config.return_value = settings

		self.assertEqual(get_sfu_presence_url(), "http://171.244.63.182:4000/internal/presence")

	@patch("meet.utils.sfu_config.get_sfu_config")
	@patch("meet.utils.sfu_config.frappe")
	def test_presence_url_falls_back_to_public_sfu_url(self, frappe_mock, get_sfu_config):
		settings = {"sfu_server_url": "https://meet.nextgrp.vn/sfu", "sfu_server_port": 3000}
		frappe_mock.conf.get.side_effect = lambda key, default=None: settings.get(key, default)
		get_sfu_config.return_value = settings

		self.assertEqual(get_sfu_presence_url(), "https://meet.nextgrp.vn/sfu/internal/presence")
