# -*- coding: utf-8 -*-
import re
from copy import deepcopy
from operator import itemgetter
from lxml import etree
import lxml.html.soupparser
import parse_html as html_parser
from consts import ALLOW_KEYWORD_TAGS, COMMENT_KEYWORDS

class Scraper(object):
    def __init__(self, html):
        html = html_parser.pre_document(html)
        html = lxml.html.soupparser.fromstring(html)
        self.html = html
        self.head = html.find('.//head')
        self.body = html.find('.//body')

        self._attrib_dic = {}
        self._make_attrib_dic(self.body, self._attrib_dic)
        self._title = None
        self._content = None
        self._comments = None

    def _make_attrib_dic(self, tree, attrib_dic):
        if tree is None:
            return
        for ele in tree:
            tag = str(ele.tag).lower()
            # remember if find one at this time
            flag = 0
            if tag in ALLOW_KEYWORD_TAGS:
                attribs = ele.get('class', '') or ele.get('id', '')
                if attribs:
                    key = attribs
                    attrib_dic.setdefault(key, []).append(ele)
                    flag = 1

            ## if find one, do not iterate its children
            if len(ele) > 0 and flag:
                self._make_attrib_dic(ele, attrib_dic)

    def _find_by_attrib_value(self, kw_re=COMMENT_KEYWORDS):
        klist = {}
        for k, elist in self._attrib_dic.items():
            if re.search(kw_re, k):
                klist[k] = elist
        return klist

    def get_title(self):
        if self._title is None:
            self._title = html_parser.get_article_title(self.html).encode('utf8')
        return self._title

    def get_content(self):
        if self._content is None:
            body = deepcopy(self.body)
            tag_dict = {}
            article_content = html_parser.grab_article(body, tag_dict)
            self._content = html_parser.get_inner_text(article_content).encode('utf8')

            tag_dict.clear()
            del body
        return self._content

    def _get_elements_text(self, elist):
        comment = ''
        for tree in elist:
            if tree.findall('.//form'):
                continue
            comment += html_parser.get_inner_text_conditionally(tree)
        return comment

    def get_comments(self):
        if not self._comments:
            kw_comments = {}
            longest_text = ''
            key_elist = self._find_by_attrib_value()
            for key, elist in key_elist.items():
                text = self._get_elements_text(elist)
                kw_comments[key] = text
                if len(text) > len(longest_text):
                    longest_text = text
            self._comments = longest_text.encode('utf8')
        return self._comments

    def find_keyword(self, keyword):
        kw_pos = {}
        title = self.get_title()
        content = self.get_content()
        comments = self.get_comments()
        if title:
            kws = re.findall(keyword, title, re.IGNORECASE)
            if kws:
                kw_pos['title'] = len(kws)
        if content:
            kws = re.findall(keyword, content, re.IGNORECASE)
            if kws:
                kw_pos['content'] = len(kws)
        if comments:
            kws = re.findall(keyword, comments, re.IGNORECASE)
            if kws:
                kw_pos['comments'] = len(kws)
        return kw_pos

