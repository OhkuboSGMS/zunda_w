import fire

from zunda_w.apis import share


def main():
    fire.Fire({
        "share": share,
    })


if __name__ == "__main__":
    main()
