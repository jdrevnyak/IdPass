"""The Pi boot config the card reader needs, without a Raspberry Pi."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "main"))

from reader_uart import plan_reader_uart, should_reboot, strip_serial_console


PI4_CONFIG = "dtparam=audio=on\n"
PI4_CMDLINE = (
    "console=serial0,115200 console=tty1 root=PARTUUID=abc rootwait\n"
)
READY_CONFIG = "dtparam=audio=on\n\n# IdPass card reader on GPIO 14 and GPIO 15\nenable_uart=1\n"
READY_CMDLINE = "console=tty1 root=PARTUUID=abc rootwait\n"


class PlanReaderUartTests(unittest.TestCase):
    def test_enables_uart_and_drops_serial_console(self):
        config, cmdline, changed = plan_reader_uart(PI4_CONFIG, PI4_CMDLINE, pi5=False)
        self.assertTrue(changed)
        self.assertIn("enable_uart=1\n", config)
        self.assertNotIn("console=serial0", cmdline)
        self.assertIn("console=tty1", cmdline)

    def test_already_ready_is_unchanged(self):
        config, cmdline, changed = plan_reader_uart(READY_CONFIG, READY_CMDLINE, pi5=False)
        self.assertFalse(changed)
        self.assertEqual(config, READY_CONFIG)
        self.assertEqual(cmdline, READY_CMDLINE)

    def test_flips_enable_uart_off(self):
        config, cmdline, changed = plan_reader_uart(
            "enable_uart=0\n", "console=tty1\n", pi5=False
        )
        self.assertTrue(changed)
        self.assertIn("enable_uart=1", config)
        self.assertNotIn("enable_uart=0", config)
        self.assertEqual(cmdline, "console=tty1\n")

    def test_pi5_adds_header_overlay(self):
        config, cmdline, changed = plan_reader_uart(READY_CONFIG, READY_CMDLINE, pi5=True)
        self.assertTrue(changed)
        self.assertIn("dtoverlay=uart0-pi5\n", config)
        self.assertEqual(cmdline, READY_CMDLINE)

    def test_pi5_overlay_with_params_is_kept(self):
        config = READY_CONFIG + "dtoverlay=uart0-pi5,ctsrts\n"
        updated, cmdline, changed = plan_reader_uart(config, READY_CMDLINE, pi5=True)
        self.assertFalse(changed)
        self.assertEqual(updated, config)
        self.assertEqual(cmdline, READY_CMDLINE)

    def test_pi5_overlay_is_not_added_twice(self):
        once, _, _ = plan_reader_uart(READY_CONFIG, READY_CMDLINE, pi5=True)
        config, cmdline, changed = plan_reader_uart(once, READY_CMDLINE, pi5=True)
        self.assertFalse(changed)
        self.assertEqual(config, once)
        self.assertEqual(cmdline, READY_CMDLINE)

    def test_does_not_treat_debug_uart_as_the_console(self):
        cmdline = "console=ttyAMA10,115200 console=tty1\n"
        self.assertEqual(
            strip_serial_console(cmdline),
            "console=ttyAMA10,115200 console=tty1",
        )
        _, updated, changed = plan_reader_uart("enable_uart=1\n", cmdline, pi5=False)
        self.assertFalse(changed)
        self.assertEqual(updated, cmdline)

    def test_commented_enable_uart_does_not_count(self):
        config, _, changed = plan_reader_uart(
            "#enable_uart=1\n", "console=tty1\n", pi5=False
        )
        self.assertTrue(changed)
        self.assertIn("\nenable_uart=1\n", config)


class RebootDecisionTests(unittest.TestCase):
    def test_reboots_for_a_new_boot_change(self):
        self.assertEqual(
            should_reboot(True, False, "", "abc", "jdrevnyak"),
            "reboot",
        )

    def test_does_not_reboot_twice_for_the_same_boot_change(self):
        self.assertEqual(
            should_reboot(True, False, "boot:abc\n", "abc", "jdrevnyak"),
            "stuck",
        )

    def test_reboots_when_the_user_is_not_in_dialout(self):
        self.assertEqual(
            should_reboot(False, True, "", "abc", "jdrevnyak"),
            "reboot",
        )

    def test_ok_when_nothing_changed(self):
        self.assertEqual(
            should_reboot(False, False, "boot:abc\n", "abc", "jdrevnyak"),
            "ok",
        )


class BootFileWriteTests(unittest.TestCase):
    def test_round_trip_on_temp_files(self):
        from reader_uart import _write_text, _read_text

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.txt")
            _write_text(path, "enable_uart=1\n")
            self.assertEqual(_read_text(path), "enable_uart=1\n")


if __name__ == "__main__":
    unittest.main()
