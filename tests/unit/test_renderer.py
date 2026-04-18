from discourse_retrieval.renderer import ThreadRenderer


def make_topic(**kwargs) -> dict:
    base = {
        "id": 1,
        "title": "My Test Topic",
        "slug": "my-test-topic",
        "created_at": "2024-03-15T10:00:00.000Z",
        "posts_count": 2,
        "category_id": 4,
        "details": {"category_name": "General"},
        "post_stream": {
            "posts": [
                {
                    "id": 101,
                    "post_number": 1,
                    "username": "alice",
                    "name": "Alice Smith",
                    "created_at": "2024-03-15T10:00:00.000Z",
                    "raw": "Hello world",
                    "cooked": "<p>Hello world</p>",
                },
                {
                    "id": 102,
                    "post_number": 2,
                    "username": "bob",
                    "name": "Bob Jones",
                    "created_at": "2024-03-16T09:30:00.000Z",
                    "raw": "Nice post!",
                    "cooked": "<p>Nice post!</p>",
                },
            ]
        },
    }
    base.update(kwargs)
    return base


class TestThreadRenderer:
    def setup_method(self):
        self.renderer = ThreadRenderer()

    def test_output_starts_with_title(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert result.startswith("# My Test Topic")

    def test_metadata_contains_category(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert "**Category**" in result
        assert "General" in result

    def test_metadata_contains_created_date(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert "**Created**" in result
        assert "2024-03-15" in result

    def test_metadata_contains_url(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert "**URL**" in result
        assert "my-test-topic" in result

    def test_post_header_contains_author_name(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert "Alice Smith" in result
        assert "Bob Jones" in result

    def test_post_header_contains_datetime(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert "2024-03-15" in result
        assert "2024-03-16" in result

    def test_post_numbered(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert "## Post 1" in result
        assert "## Post 2" in result

    def test_raw_content_used_when_present(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert "Hello world" in result
        # should NOT contain raw HTML tags
        assert "<p>" not in result

    def test_html_cooked_used_when_raw_absent(self):
        topic = make_topic()
        topic["post_stream"]["posts"][0].pop("raw")
        result = self.renderer.render(topic)
        # html2text converts <p>Hello world</p> to "Hello world"
        assert "Hello world" in result
        assert "<p>" not in result

    def test_html_cooked_used_when_raw_empty(self):
        topic = make_topic()
        topic["post_stream"]["posts"][0]["raw"] = ""
        result = self.renderer.render(topic)
        assert "Hello world" in result

    def test_separator_between_posts(self):
        topic = make_topic()
        result = self.renderer.render(topic)
        assert "---" in result
