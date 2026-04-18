import html2text


class ThreadRenderer:
    def __init__(self) -> None:
        self._h2t = html2text.HTML2Text()
        self._h2t.ignore_links = False
        self._h2t.body_width = 0  # no line wrapping

    def render(self, topic: dict) -> str:
        title = topic["title"]
        slug = topic["slug"]
        created_at = topic["created_at"][:10]  # YYYY-MM-DD
        category_name = topic.get("details", {}).get(
            "category_name", str(topic.get("category_id", ""))
        )
        topic_url = f"<topic-url>/{slug}/{topic['id']}"

        parts = [
            f"# {title}",
            "",
            f"**Category**: {category_name}  ",
            f"**Created**: {created_at}  ",
            f"**URL**: {topic_url}",
            "",
            "---",
            "",
        ]

        posts = topic.get("post_stream", {}).get("posts", [])
        for post in posts:
            author = post.get("name") or post.get("username", "unknown")
            post_dt = post["created_at"].replace("T", " ").replace(".000Z", "Z")
            parts.append(f"## Post {post['post_number']} - {author} ({post_dt})")
            parts.append("")

            raw = post.get("raw", "")
            if raw:
                parts.append(raw)
            else:
                parts.append(self._h2t.handle(post.get("cooked", "")).strip())

            parts.append("")
            parts.append("---")
            parts.append("")

        return "\n".join(parts)
