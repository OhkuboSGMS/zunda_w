import fire

from zunda_w.apis import share
from zunda_w.apis.hatena import generate_interview_blog


def main():
    fire.Fire({
        "share": share,
        "hatena_interview_blog_html": generate_interview_blog
    })


if __name__ == "__main__":
    main()
