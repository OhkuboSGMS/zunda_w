from pathlib import Path

from jinja2 import Environment, meta, Template


def render(template_file: str, blog_kwargs: dict) -> str:
    """
    テンプレートのmarkdownを読み込んで、jinja2のテンプレート機能を使って、プレースホルダを埋める
    :param template_file: 適用するmarkdownテンプレートファイル
    :param blog_kwargs: placeholderに埋める値
    :return:
    """
    if not Path(template_file).exists():
        raise FileNotFoundError(f"Template file not found: {template_file}")
    variables = get_template_variables(template_file)
    if not set(blog_kwargs.keys()).issuperset(variables):
        raise ValueError(
            f"Template variables are not matched with kwargs:追加でこの要素が必要です:{variables - set(blog_kwargs.keys())}")
    with open(template_file, "r", encoding="utf-8") as f:
        template = Template(f.read())
    return template.render(**blog_kwargs)


def get_template_variables(template_file: str) -> set:
    # Jinja2環境を設定
    template_ast = Environment().parse(Path(template_file).read_text(encoding="utf-8"))
    # テンプレート内のすべての変数名を取得
    variables = meta.find_undeclared_variables(template_ast)
    return variables


def _sample():
    template_file = "config/publish/blog_template.md"
    kwargs = {
        "episode_number": "210",
        "podcast_url": "https://anchor.fm/s/example",
        "show_note": "This is a show note",
        "transcript": "This is a transcript",
    }
    variables = get_template_variables(template_file)
    # テンプレート内の変数名を表示
    print(variables)
    assert set(
        kwargs.keys()) >= variables, f"Template variables are not matched with kwargs:{kwargs.keys()} は包含しない {variables}を"
    result = render(template_file, blog_kwargs=kwargs)
    Path("test_blog_post.md").write_text(result, encoding="utf-8")


if __name__ == '__main__':
    _sample()
