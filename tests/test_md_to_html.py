import pprint

import markdown


def test_convert():
    markdown_text = """# Sample Markdown

This is some basic, sample markdown.

## Second Heading

 * Unordered lists, and:
  1. One
  1. Two
  1. Three
 * More

> Blockquote

And **bold**, *italics*, and even *italics and later **bold***. Even ~~strikethrough~~. [A link](https://markdowntohtml.com) to somewhere.

And code highlighting:

```js
var foo = 'bar';

function baz(s) {
   return foo + ':' + s;
}
"""
    raw_html = markdown.markdown(text=markdown_text, extensions=["mdx_linkify"])
    with open("markdonw.html", "w") as f:
        f.write(raw_html)
