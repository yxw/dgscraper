# -*- coding: utf-8 -*-
MAGICSPLITTER = '@#NpZb#@'
TAGS_TO_IGNORE = ["head", "style", "script", "noscript", "<built-in function comment>", "option"]
TAGS_IN_NEWLINE = ["p", "div", "h1", "h2","h3", "h4", "h5", "h6", "br", "li"]

FLAG_STRIP_UNLIKELYS = 0x1
FLAG_WEIGHT_CLASSES = 0x2
FLAG_CLEAN_CONDITIONALLY = 0x4
ALL_FLAGS = 0x1 | 0x2 | 0x4

ALLOW_KEYWORD_TAGS = ['div','span','ul','ol','td']
COMMENT_KEYWORDS = r'answer|comment|response|reply'
