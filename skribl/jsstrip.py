"""Remove comments from JavaScript on the way OUT, never in the source.

WHY THIS EXISTS. 32% of app.js is comment text, and app.js is the largest single
thing a viewer of a shared link downloads. The comments are the asset — this
project's whole method is written in them — so the size problem and the source
must be solved separately: the file on disk keeps every word, and the bytes a
browser parses do not carry them. `verify_player_isolation.py` measures
`r.body()`, the decoded response, which is exactly the surface this changes.

NOT A REGEX, AND THE REASON IS ONE LINE OF app.js:

    const re = /https:\\/\\//g;

A regex that deletes `//...` to end of line reads the `//` inside that literal as
a comment and eats the rest of the statement. The inverse trap is a string
containing `/*`. Both require knowing whether a `/` starts a regular expression
or is a division operator, and that question is not answerable by pattern
matching — it needs the previous significant token, which needs a scanner. So
this is a scanner: an ECMAScript lexer that tracks the goal symbol the way the
grammar does, and treats comments as just one of the things it can recognise.

WHAT IS KEPT ON PURPOSE. Legal banners. `gifenc.min.js` opens with `/*!` naming
its MIT licence and copyright holder, and `mp4-muxer.min.js` opens with its
provenance. Serving a copy with the notice removed is a licence question, not a
size question, so `/*!` and any comment mentioning @license/@preserve/Copyright
survives. Terser and every other minifier draw the line in the same place.

WHAT THE OUTPUT PRESERVES. A block comment spanning lines is a LineTerminator
for automatic semicolon insertion, so a multi-line comment leaves a newline
behind rather than vanishing; a single-line one leaves a space, because `a/**/b`
must not become `ab`. Line comments keep their terminating newline. Nothing else
moves: this is not a minifier, it does not touch whitespace, rename anything, or
reorder a single byte of code.

THE FALLBACK IS THE POINT. `strip_bytes` returns the ORIGINAL bytes if anything
at all goes wrong — an exception, a decode failure, or a token stream that does
not survive the round trip. A slightly larger file is a non-event; a corrupted
app.js is every shared link on the site. Correctness of the strip itself is
proved in `verify_jsstrip.py` by a real JavaScript engine and by the player's
pixels, because a lexer checking its own work is a lexer agreeing with itself.
"""

# Keywords after which a `/` begins a regular expression rather than a division:
# `return /x/` is a regex, `a /x/` is two divisions. `of` and `in` are here as
# contextual keywords; misreading either way is only reachable with a `/` next.
_REGEX_AFTER_KEYWORD = frozenset("""
    return typeof instanceof in of new delete void throw case do else yield
    await let const var if while for with switch catch finally try default
""".split())

# `{` in statement position opens a block; anywhere else it is an object literal
# or a class body. The distinction matters only for what a following `}` implies
# about the NEXT `/`, which is why it is tracked rather than guessed.
_BLOCK_BEFORE_PUNCT = frozenset({";", "{", "}", ")", "=>"})
_BLOCK_BEFORE_KEYWORD = frozenset({"else", "do", "try", "finally"})

# A `)` closing one of these heads is followed by a statement, so `if (x) /re/.test(s)`
# is a regex; `(a + b) / 2` is division.
_STATEMENT_HEAD = frozenset({"if", "while", "for", "with", "switch", "catch"})

_LEGAL = ("@license", "@preserve", "@cc_on", "copyright", "©", "licence", "license")

# Longest first: the scanner takes the first that matches, so `>>>=` must be
# offered before `>>>`, or the tail is re-lexed as a separate token.
_PUNCTUATORS = sorted(
    """>>>= ... === !== **= <<= >>= &&= ||= ??= >>> => == != <= >= && || ?? ?. ++ --
       += -= *= /= %= &= |= ^= ** << >> { } ( ) [ ] ; , < > + - * / % & | ^ ! ~ ? :
       = . #""".split(),
    key=len, reverse=True)

_LINE_TERMINATORS = "\n\r\u2028\u2029"


class _Token:
    __slots__ = ("kind", "value", "start", "end")

    def __init__(self, kind, value, start, end):
        self.kind, self.value, self.start, self.end = kind, value, start, end


def _is_id_start(ch):
    # Non-ASCII is accepted wholesale: identifiers may contain any ID_Continue
    # codepoint, and for comment-finding purposes the only thing that matters is
    # that a run of them is ONE token and is not mistaken for an operator.
    return ch.isalpha() or ch in "_$" or ord(ch) > 127


def _is_id_part(ch):
    return _is_id_start(ch) or ch.isdigit()


class _Lexer:
    """Yields tokens, including comments. The caller decides what to drop."""

    def __init__(self, src):
        self.src = src
        self.i = 0
        self.n = len(src)
        self.prev = None            # last SIGNIFICANT token (comments skipped)
        self.parens = []            # per `(`: does its `)` end a statement head?
        self.braces = []            # per `{`: is it a block?
        self.paren_ends_head = False
        self.brace_was_block = True

    # -- the question the whole file exists to answer -------------------------
    def _regex_allowed(self):
        p = self.prev
        if p is None:
            return True
        if p.kind == "name":
            return p.value in _REGEX_AFTER_KEYWORD
        if p.kind in ("number", "string", "template", "regex"):
            return False
        # punctuator
        if p.value == ")":
            return self.paren_ends_head
        if p.value == "}":
            return self.brace_was_block
        if p.value in ("]", "++", "--"):
            return False
        return True

    def _read_string(self, quote):
        i, src = self.i + 1, self.src
        while i < self.n:
            ch = src[i]
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                return i + 1
            if ch in "\n\r":
                # Unterminated: bail rather than swallow the rest of the file.
                raise ValueError(f"unterminated string at {self.i}")
            i += 1
        raise ValueError(f"unterminated string at {self.i}")

    def _read_template(self):
        """A template literal, including any `${ ... }` and what nests inside.

        Substitutions can hold anything — strings, regexes, comments, more
        templates — so this recurses through a nested lexer rather than
        scanning for the next backtick, which is the naive version's bug.
        """
        i, src = self.i + 1, self.src
        while i < self.n:
            ch = src[i]
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                return i + 1
            if ch == "$" and i + 1 < self.n and src[i + 1] == "{":
                inner = _Lexer(src)
                inner.i = i + 2
                depth = 1
                for tok in inner:
                    if tok.kind == "punct" and tok.value == "{":
                        depth += 1
                    elif tok.kind == "punct" and tok.value == "}":
                        depth -= 1
                        if depth == 0:
                            break
                else:
                    raise ValueError(f"unterminated template at {self.i}")
                i = inner.i
                continue
            i += 1
        raise ValueError(f"unterminated template at {self.i}")

    def _read_regex(self):
        i, src, in_class = self.i + 1, self.src, False
        while i < self.n:
            ch = src[i]
            if ch == "\\":
                i += 2
                continue
            if ch == "[":
                in_class = True
            elif ch == "]":
                in_class = False
            elif ch == "/" and not in_class:
                i += 1
                while i < self.n and _is_id_part(src[i]):   # flags
                    i += 1
                return i
            elif ch in _LINE_TERMINATORS:
                raise ValueError(f"unterminated regex at {self.i}")
            i += 1
        raise ValueError(f"unterminated regex at {self.i}")

    def __iter__(self):
        src = self.src
        while self.i < self.n:
            start = self.i
            ch = src[start]

            if ch in " \t\v\f\ufeff\xa0" or ch in _LINE_TERMINATORS:
                self.i += 1
                continue

            if ch == "/" and start + 1 < self.n:
                nxt = src[start + 1]
                if nxt == "/":
                    j = start + 2
                    while j < self.n and src[j] not in _LINE_TERMINATORS:
                        j += 1
                    self.i = j
                    yield _Token("line_comment", src[start:j], start, j)
                    continue
                if nxt == "*":
                    j = src.find("*/", start + 2)
                    if j < 0:
                        raise ValueError(f"unterminated block comment at {start}")
                    j += 2
                    self.i = j
                    yield _Token("block_comment", src[start:j], start, j)
                    continue
                if self._regex_allowed():
                    self.i = self._read_regex()
                    tok = _Token("regex", src[start:self.i], start, self.i)
                    self.prev = tok
                    yield tok
                    continue

            if ch in "'\"":
                self.i = self._read_string(ch)
                tok = _Token("string", src[start:self.i], start, self.i)
                self.prev = tok
                yield tok
                continue

            if ch == "`":
                self.i = self._read_template()
                tok = _Token("template", src[start:self.i], start, self.i)
                self.prev = tok
                yield tok
                continue

            if ch.isdigit() or (ch == "." and start + 1 < self.n
                                and src[start + 1].isdigit()):
                j = start
                while j < self.n and (_is_id_part(src[j]) or src[j] == "."
                                      or (src[j] in "+-" and src[j - 1] in "eE"
                                          and not src[start:j].lower().startswith("0x"))):
                    j += 1
                self.i = j
                tok = _Token("number", src[start:j], start, j)
                self.prev = tok
                yield tok
                continue

            if _is_id_start(ch):
                j = start + 1
                while j < self.n and _is_id_part(src[j]):
                    j += 1
                self.i = j
                tok = _Token("name", src[start:j], start, j)
                self.prev = tok
                yield tok
                continue

            for p in _PUNCTUATORS:
                if src.startswith(p, start):
                    self.i = start + len(p)
                    if p == "(":
                        self.parens.append(
                            self.prev is not None and self.prev.kind == "name"
                            and self.prev.value in _STATEMENT_HEAD)
                    elif p == ")":
                        self.paren_ends_head = self.parens.pop() if self.parens else False
                    elif p == "{":
                        prev = self.prev
                        if prev is None:
                            block = True
                        elif prev.kind == "name":
                            block = (prev.value in _BLOCK_BEFORE_KEYWORD
                                     or prev.value not in _REGEX_AFTER_KEYWORD)
                        elif prev.kind == "punct":
                            block = prev.value in _BLOCK_BEFORE_PUNCT
                        else:
                            block = False
                        self.braces.append(block)
                    elif p == "}":
                        self.brace_was_block = self.braces.pop() if self.braces else True
                    tok = _Token("punct", p, start, self.i)
                    self.prev = tok
                    yield tok
                    break
            else:
                raise ValueError(f"unexpected character {ch!r} at {start}")


def _is_legal(text):
    """Licence and attribution banners are not size, they are terms."""
    if text.startswith("/*!"):
        return True
    low = text.lower()
    return any(marker in low for marker in _LEGAL)


def _significant(src):
    return [(t.kind, t.value) for t in _Lexer(src)
            if t.kind not in ("line_comment", "block_comment")]


def strip_comments(src, keep_banner=False):
    """Return `src` with non-legal comments removed. Raises on anything odd.

    `keep_banner` preserves a leading block comment whatever it says, for
    VENDORED artifacts only. mp4-muxer.min.js's banner names its upstream
    version and warns about SRI without using the word licence, so a rule that
    only looks for `/*!` throws away the provenance of code we did not write.
    It is off by default because our own files open with block comments too —
    audioloop, looptrim and photofit all do, and keeping theirs put 4,491 bytes
    back onto the player for no benefit to anyone.
    """
    out, last = [], 0
    for first, tok in enumerate(_Lexer(src)):
        if tok.kind not in ("line_comment", "block_comment"):
            continue
        if keep_banner and first == 0 and tok.kind == "block_comment":
            continue
        if _is_legal(tok.value):
            continue
        chunk = src[last:tok.start]
        # A comment on its own line leaves its indentation behind, and app.js
        # has thousands of those. Horizontal whitespace on a line that now holds
        # nothing else cannot move a token boundary or change ASI — the newline
        # itself is untouched — so it goes with the comment it was indenting.
        trimmed = chunk.rstrip(" \t")
        if not trimmed or trimmed[-1] in _LINE_TERMINATORS:
            chunk = trimmed
        out.append(chunk)
        if tok.kind == "line_comment":
            # The terminating newline is not part of the token, so ASI is safe
            # without adding anything.
            pass
        elif any(ch in tok.value for ch in _LINE_TERMINATORS):
            out.append("\n")        # a multi-line comment IS a LineTerminator
        else:
            out.append(" ")         # `a/**/b` must not become `ab`
        last = tok.end
    out.append(src[last:])
    return "".join(out)


def _collapse_whitespace(src):
    """Collapse each inter-token gap containing a line terminator to "\\n".

    Token-aware for the same reason strip_comments is: a regex can hold spaces,
    a template literal can hold anything, and both are single tokens here, so
    their interiors are untouchable BY CONSTRUCTION — only the gaps between
    tokens are visited. Keeping exactly one newline in any gap that had one
    preserves automatic semicolon insertion exactly (ASI asks whether a
    LineTerminator separates two tokens, never how many); gaps on one line are
    left alone, so this removes indentation and blank lines and nothing else.
    """
    out, last = [], 0
    for tok in _Lexer(src):
        gap = src[last:tok.start]
        if gap:
            if any(ch in gap for ch in _LINE_TERMINATORS):
                out.append("\n")
            else:
                out.append(gap)
        out.append(src[tok.start:tok.end])
        last = tok.end
    tail = src[last:]
    if tail:
        out.append("\n" if any(ch in tail for ch in _LINE_TERMINATORS) else tail)
    return "".join(out)


def strip_bytes(data, name=""):
    """Comment-stripped UTF-8 bytes, or `data` unchanged if anything is off.

    `name` is the request path or filename; it selects the vendored-banner rule
    described on strip_comments. A `.min.js` in this tree is by definition a
    build artifact from somewhere else — nothing here is minified in place.

    Every failure mode here — undecodable bytes, a lexer that hits something it
    does not recognise, a token stream that changed — resolves to serving the
    file exactly as it is on disk. That is a few kilobytes; the alternative is a
    broken player on every shared link.
    """
    try:
        src = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    try:
        stripped = strip_comments(src, keep_banner=name.endswith(".min.js"))
        stripped = _collapse_whitespace(stripped)
        # Cheap round trip, on the COMBINED result of both passes. It cannot
        # prove the lexer read the file correctly (it would have to be right to
        # check), but it does catch a strip or collapse that removed or merged
        # real tokens, which is the failure that matters.
        if _significant(stripped) != _significant(src):
            return data
    except Exception:
        return data
    packed = stripped.encode("utf-8")
    return packed if len(packed) < len(data) else data
