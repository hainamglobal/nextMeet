from unittest import TestCase

from meet.utils.sfu_config import _build_sfu_presence_url


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
