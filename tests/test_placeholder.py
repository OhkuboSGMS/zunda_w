from pathlib import Path

from jinja2 import Template

from zunda_w.srt_ops import srt_as_interview_blog_content


def test_html_placeholder():
    """
    HTMLのプレースホルダを埋める
    :return:
    """
    template = "<html><head><title>{{ title }}</title></head><body>{{ content }}</body></html>"
    keywords = {"title": "This is a title", "content": "This is a content"}
    result = Template(template).render(**keywords)
    assert result == "<html><head><title>This is a title</title></head><body>This is a content</body></html>"


def test_avatar_html_parts():
    file = "zunda_w/apis/hatena/hatena_comment_with_avatar.html"
    assert Path(file).exists()

    template = Path(file).read_text(encoding="utf-8")
    keywords = {"img_url": "https://example.com/avatar.jpg", "color": "#333", "name": "Zunda",
                "text": "This is a comment"}
    result = Template(template).render(**keywords)


def test_srt_interview_blog(test_srt_1):
    srt_content = Path(test_srt_1).read_text(encoding="UTF-8")
    label_map = {"2": "まっと", "1": "おおくぼ"}
    publish_map = {
        "2": {"avatar": "https://picsum.photos/seed/picsum/400", "color": "orange"},
        "1": {"avatar": "https://picsum.photos/seed/picsum/400", "color": "green"}
    }
    template_file = "../zunda_w/apis/hatena/hatena_comment_with_avatar.html"
    result = srt_as_interview_blog_content(srt_content, template_file, label_map, publish_map)
