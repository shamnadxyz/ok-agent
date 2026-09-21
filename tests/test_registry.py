import unittest

from ok_agent.tools.registry import validate_tool
from ok_agent.tools.types import JSONSchema


class ValidateToolTestCase(unittest.TestCase):
    def setUp(self):
        self.parameter_schema: JSONSchema = {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "shell command",
                },
                "timeout": {
                    "type": "number",
                    "description": "command timeout (default: 10)",
                },
                "input": {
                    "type": "string",
                    "description": "text sent to stdin",
                },
            },
            "required": ["cmd"],
        }

    def test_shell_tool_empty(self):
        self.assertNotEqual(validate_tool({}, self.parameter_schema), None)

    def test_shell_tool_only_cmd(self):
        self.assertEqual(
            validate_tool({"cmd": "ls"}, self.parameter_schema), None
        )

    def test_shell_tool_full_args(self):
        self.assertEqual(
            validate_tool({"cmd": "ls", "timeout": 30}, self.parameter_schema),
            None,
        )

    def test_shell_tool_timeout_string_fail(self):

        self.assertNotEqual(
            validate_tool(
                {"cmd": "ls", "timeout": "20"}, self.parameter_schema
            ),
            None,
        )

    def test_shell_tool_int_fail(self):
        self.assertNotEqual(
            validate_tool({"cmd": 123}, self.parameter_schema), None
        )

    def test_shell_tool_bool_fail(self):
        self.assertNotEqual(
            validate_tool({"cmd": True}, self.parameter_schema), None
        )

    def test_shell_tool_list_fail(self):
        self.assertNotEqual(
            validate_tool({"cmd": [1, 2]}, self.parameter_schema), None
        )

    def test_shell_tool_dict_fail(self):
        self.assertNotEqual(
            validate_tool({"cmd": {"test": 1}}, self.parameter_schema), None
        )


if __name__ == "__main__":
    unittest.main()
