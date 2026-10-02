import unittest

from ok_agent.tools.shell_tool import check_guardrails


class ValidatorObjectPropertiesTestCase(unittest.TestCase):
    def test_guardrail_trigger(self):
        tests = [
            "ls /",
            "rm -rf docs",
            "find / -name *.py",
            "find ////// -name *.py",
            "ls && find / -name *.md",
            "ls ~; find /;",
            "ls ~/////; find /;",
            "ls -R",
            "ls ./;ls -R",
        ]

        for command in tests:
            with self.subTest(value=command):
                self.assertIsNotNone(check_guardrails(command))

    def test_guardrail_noop(self):
        tests = [
            "ls",
            "cat README.md",
            "cd /tmp && python3 download_eporner.py",
        ]

        for command in tests:
            with self.subTest(value=command):
                self.assertIsNone(check_guardrails(command))


if __name__ == "__main__":
    unittest.main()
