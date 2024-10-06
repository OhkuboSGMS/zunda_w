from dotenv import load_dotenv

from zunda_w.apis.hatena.hatena import post_blog

sample_blog_md = "tests/test_data/test_hatena_blog.md"


def _sample_post_blog():
    md = sample_blog_md
    title = "Test Post"
    categories = [str(f"TAG:{i}") for i in range(4)]
    status, result = post_blog(title, open(md).read(), categories, draft=True, )
    print(status, result)


def main():
    load_dotenv()
    _sample_post_blog()


if __name__ == "__main__":
    main()
