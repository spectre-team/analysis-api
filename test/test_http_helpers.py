import unittest

import http_helpers as hh


class TestMatchItem(unittest.TestCase):
    def test_matches_key_by_value(self):
        collection = {"blah": 1, "wololo": 2}
        blah_matcher = hh.Matcher(key="blah", value=1)
        self.assertTrue(hh._match_item(blah_matcher, collection))
        wololo_matcher = hh.Matcher(key="wololo", value=1)
        self.assertFalse(hh._match_item(wololo_matcher, collection))


class TestMatching(unittest.TestCase):
    def test_preserves_matching_only(self):
        collection = [
            {"a": 1, "b": 1},
            {"a": 2, "b": 2},
            {"a": 1, "b": 3},
        ]
        matcher = hh.Matcher(key="a", value=1)
        matching = hh._matching(matcher, collection)
        self.assertEqual(2, len(matching))
        self.assertEqual(1, matching[0]["b"])
        self.assertEqual(3, matching[1]["b"])


class TestSelect(unittest.TestCase):
    def test(self):
        expected_selection = {
            "title": "Person",
            "type": "object",
            "properties": {
                "firstName": {"type": "string"},
                "lastName": {"type": "string"},
                "age": {
                    "description": "Age in years",
                    "type": "integer",
                    "minimum": 0
                }
            },
            "required": ["firstName", "lastName"]
        }
        some_json = [
            {
                "aspect": "some_aspect",
                "friendly_name": "User-readable aspect name (will be displayed)",
                "description": "Longer description<br/>with explanation",
                "query_format": expected_selection,
                "output_type": "table"
            },
            {
                "aspect": "none",
                "friendly_name": "User-readable aspect name (will be displayed)",
                "description": "Longer description<br/>with explanation",
                "query_format": {},
                "output_type": "table"
            }
        ]
        selectors = [
            hh.Matcher(key="aspect", value="some_aspect"), "query_format"
        ]
        selected = hh._select(some_json, selectors)
        self.assertDictEqual(expected_selection, selected)
