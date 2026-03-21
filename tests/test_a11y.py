"""Unit tests for control/a11y_parser.py."""

from control.a11y_parser import parse_tree, match_target


SAMPLE_TREE = (
    "tag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)\n"
    "label\tHome\tHome\t\t\t(1833, 854)\t(40, 17)\n"
    "push-button\tChromium Web Browser\t\"\"\t\t\t(0, 33)\t(70, 64)\n"
    "push-button\tSend\tSend\t\t\t(100, 200)\t(80, 30)\n"
)


class TestParseTree:

    def test_normal_lines(self):
        nodes = parse_tree(SAMPLE_TREE)
        assert len(nodes) == 3
        assert nodes[0]["tag"] == "label"
        assert nodes[0]["name"] == "Home"
        assert nodes[0]["x"] == 1833
        assert nodes[0]["y"] == 854
        assert nodes[0]["w"] == 40
        assert nodes[0]["h"] == 17

    def test_button_fields(self):
        nodes = parse_tree(SAMPLE_TREE)
        send = nodes[2]
        assert send["tag"] == "push-button"
        assert send["name"] == "Send"
        assert send["x"] == 100
        assert send["y"] == 200
        assert send["w"] == 80
        assert send["h"] == 30

    def test_empty_input(self):
        assert parse_tree("") == []
        assert parse_tree(None) == []

    def test_header_only(self):
        tree = "tag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)"
        assert parse_tree(tree) == []

    def test_malformed_lines_skipped(self):
        """Lines with wrong field count or empty tag are skipped."""
        tree = (
            "tag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)\n"
            "label\tHome\tHome\t\t\t(100, 200)\t(40, 17)\n"
            "this line has no tabs\n"
            "\t\t\t\t\t(500, 600)\t(10, 10)\n"  # empty tag
            "button\tOK\tOK\t\t\t(300, 400)\t(50, 25)\n"
        )
        nodes = parse_tree(tree)
        assert len(nodes) == 2
        assert nodes[0]["tag"] == "label"
        assert nodes[1]["tag"] == "button"


class TestMatchTarget:

    def _make_nodes(self):
        return [
            {"tag": "label", "name": "Home", "text": "Home",
             "class": "", "description": "",
             "x": 1833, "y": 854, "w": 40, "h": 17},
            {"tag": "push-button", "name": "Send", "text": "Send",
             "class": "", "description": "",
             "x": 100, "y": 200, "w": 80, "h": 30},
            {"tag": "panel", "name": "Main", "text": "",
             "class": "", "description": "",
             "x": 0, "y": 0, "w": 1920, "h": 1080},
        ]

    def test_contains_point_smallest_area(self):
        """Click at (150, 210) -- both Send button and Main panel contain it.
        Send button is smaller, so it wins."""
        nodes = self._make_nodes()
        result = match_target(nodes, 150, 210)
        assert result["target_matched"] is True
        assert result["target_name"] == "Send"
        assert result["target_match_method"] == "contains_point"
        assert result["target_bounds"] == {"x": 100, "y": 200, "w": 80, "h": 30}

    def test_nearest_center_fallback(self):
        """Click just outside a button, within 50px of its center."""
        nodes = [
            {"tag": "push-button", "name": "Send", "text": "Send",
             "class": "", "description": "",
             "x": 100, "y": 200, "w": 80, "h": 30},
        ]
        # Click at (185, 215) -- just outside Send (100+80=180), center (140, 215), dist=45px
        result = match_target(nodes, 185, 215)
        assert result["target_matched"] is True
        assert result["target_match_method"] == "nearest_center"

    def test_no_match(self):
        """Click far from all nodes."""
        nodes = [
            {"tag": "button", "name": "OK", "text": "OK",
             "class": "", "description": "",
             "x": 100, "y": 100, "w": 50, "h": 30},
        ]
        result = match_target(nodes, 900, 900)
        assert result["target_matched"] is False
        assert result["target_match_method"] == "none"

    def test_empty_nodes(self):
        result = match_target([], 100, 200)
        assert result["target_matched"] is False
