import unittest

from ok_agent.validator import (
    ArraySchema,
    JSONSchema,
    validate_array,
    validate_object,
)
from ok_agent.validator.validator import ValidationError


class ValidatorObjectPropertiesTestCase(unittest.TestCase):
    def setUp(self):
        self.schema: JSONSchema = {
            "type": "object",
            "properties": {
                "array": {"type": "array"},
                "boolean": {"type": "boolean"},
                "integer": {"type": "integer"},
                "number": {"type": "number"},
                "object": {"type": "object"},
                "string": {"type": "string"},
            },
        }

    def test_empty(self):
        self.assertEqual(validate_object({}, self.schema), None)

    def test_bool_pass(self):
        bools = [True, False]

        for value in bools:
            with self.subTest(value=value):
                self.assertIsNone(
                    validate_object({"boolean": value}, self.schema)
                )

    def test_bool_fail(self):
        not_bools = [
            "100",
            (1, 2),
            [1, 2],
            {"one": 1},
            1.1,
            None,
        ]

        for value in not_bools:
            with self.subTest(value=value):
                self.assertRaises(
                    ValidationError,
                    validate_object,
                    {"boolean": value},
                    self.schema,
                )

    def test_string_pass(self):
        strings = [
            "Hello",
            "",
        ]

        for value in strings:
            with self.subTest(value=value):
                self.assertIsNone(
                    validate_object({"string": value}, self.schema)
                )

    def test_string_fail(self):
        not_strings = [
            100,
            [1, 2],
            (1, 2),
            {"one": 1},
            True,
            1.1,
            None,
        ]

        for value in not_strings:
            with self.subTest(value=value):
                self.assertRaises(
                    ValidationError,
                    validate_object,
                    {"string": value},
                    self.schema,
                )

    def test_object_pass(self):
        objects = [
            {"one": "two"},
            {},
        ]

        for value in objects:
            with self.subTest(value=value):
                self.assertIsNone(
                    validate_object({"object": value}, self.schema)
                )

    def test_object_fail(self):
        not_objects = [
            "100",
            (1, 2),
            1.1,
            123,
            True,
            [1, 2],
            None,
        ]

        for value in not_objects:
            with self.subTest(value=value):
                self.assertRaises(
                    ValidationError,
                    validate_object,
                    {"object": value},
                    self.schema,
                )

    def test_integer_pass(self):
        integers = [1, 2, -1, 0]

        for value in integers:
            with self.subTest(value=value):
                self.assertIsNone(
                    validate_object({"integer": value}, self.schema)
                )

    def test_integer_fail(self):
        not_integers = [
            "100",
            [1, 2],
            (1, 2),
            {"one": 1},
            True,
            1.1,
            None,
        ]

        for value in not_integers:
            with self.subTest(value=value):
                self.assertRaises(
                    ValidationError,
                    validate_object,
                    {"integer": value},
                    self.schema,
                )

    def test_array_pass(self):
        arrays = [[1], []]

        for value in arrays:
            with self.subTest(value=value):
                self.assertIsNone(
                    validate_object({"array": value}, self.schema)
                )

    def test_array_fail(self):
        not_arrays = [
            "100",
            (1, 2),
            {"one": 1},
            True,
            1.1,
            1,
            None,
        ]

        for value in not_arrays:
            with self.subTest(value=value):
                self.assertRaises(
                    ValidationError,
                    validate_object,
                    {"array": value},
                    self.schema,
                )

    def test_number_pass(self):
        numbers = [1, 2, -1, 0, 1.1]

        for value in numbers:
            with self.subTest(value=value):
                self.assertIsNone(
                    validate_object({"number": value}, self.schema)
                )

    def test_number_fail(self):
        not_numbers = [
            "100",
            [1, 2],
            (1, 2),
            {"one": 1},
            True,
            None,
        ]

        for value in not_numbers:
            with self.subTest(value=value):
                self.assertRaises(
                    ValidationError,
                    validate_object,
                    {"number": value},
                    self.schema,
                )


class ValidatorObjectRequiredTestCase(unittest.TestCase):
    def setUp(self):
        self.schema: JSONSchema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["content", "path"],
        }

    def test_object_pass(self):
        tests = [
            {"path": "README.md", "content": "# Readme"},
            {"path": "README.md", "content": ""},
        ]

        for value in tests:
            with self.subTest(value=value):
                self.assertIsNone(validate_object(value, self.schema))

    def test_object_fail(self):
        tests = [
            {"path": "README.md", "content": None},
            {"path": "README.md"},
            {"content": "README.md"},
            {"content": None},
            {"content": None},
            {"path": None, "content": None},
            {},
        ]

        for value in tests:
            with self.subTest(value=value):
                self.assertRaises(
                    ValidationError,
                    validate_object,
                    value,
                    self.schema,
                )


class ValidatorArrayTestCase(unittest.TestCase):
    def setUp(self):
        self.schema: ArraySchema = {
            "type": "array",
            "items": {"type": "integer"},
        }

    def test_array_pass(self):
        tests = [[1, 2, 3], [4, -5], []]

        for value in tests:
            with self.subTest(value=value):
                self.assertIsNone(validate_array(value, self.schema))

    def test_array_fail(self):
        tests = [[1.1, 2, 3], ["hello", -5], [(1, 2)]]

        for value in tests:
            with self.subTest(value=value):
                self.assertRaises(
                    ValidationError,
                    validate_array,
                    value,
                    self.schema,
                )


if __name__ == "__main__":
    unittest.main()
