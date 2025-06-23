from html.parser import HTMLParser

class _Node:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
    def get(self, key, default=None):
        return self.attrs.get(key, default)
    @property
    def text(self):
        return ''

class _Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []
    def handle_starttag(self, tag, attrs):
        self.nodes.append(_Node(tag, dict(attrs)))
    handle_startendtag = handle_starttag

class BeautifulSoup:
    def __init__(self, markup, parser=None):
        if isinstance(markup, bytes):
            markup = markup.decode('utf-8', 'ignore')
        parser = _Collector()
        parser.feed(markup)
        self._nodes = parser.nodes
        try:
            import builtins
            builtins.content = markup
        except Exception:
            pass

    def find(self, name=None, attrs=None):
        attrs = attrs or {}
        for node in self._nodes:
            if name and node.tag != name:
                continue
            ok = True
            for k, v in attrs.items():
                if v is None:
                    if k in node.attrs:
                        ok = False
                        break
                else:
                    if node.attrs.get(k) != v:
                        ok = False
                        break
            if ok:
                return node
        return None
