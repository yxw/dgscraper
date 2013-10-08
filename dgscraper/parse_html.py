# -*- coding: utf-8 -*-
"""Code to manipulate HTML"""

import re, sys
import lxml
import lxml.html.soupparser
from lxml import etree
from lxml.html.clean import Cleaner
from BeautifulSoup import BeautifulSoup
from consts import *

def _get_class_id_string(e):
    class_name = e.get('class', '')
    id_name = e.get('id', '')
    return MAGICSPLITTER.join([class_name, id_name])

def match_node_class_id(reg, node):
    """
    match the node's class or id attrib with reg
    """
    class_name = node.get('class')
    if class_name:
        return re.match(reg, class_name, re.I)
    id_name = node.get('id')
    if id_name:
        return re.match(reg, id_name, re.I)
    return None

def _get_text(tree):
    text = ''
    tag = str(tree.tag).lower()
    if tag in TAGS_TO_IGNORE:
        return ''
    if tree.text != None:
        text += tree.text
    for child in tree:
        text += _get_text(child)

    if tag in TAGS_IN_NEWLINE:
        text += '\n'
    else:
        text += ' '
    if tree.tail != None:
        text += tree.tail
    return text

def is_flag_active(flag):
    return (ALL_FLAGS & flag) > 0

def add_flag(flag):
    ALL_FLAGS = ALL_FLAGS | flag

def remove_flag(flag):
    ALL_FLAGS = ALL_FLAGS & ~flag

def get_inner_text(e, normalize_space=True):
    re_normalize = '(\s)\s{1,}'
    text = _get_text(e)
    if normalize_space:
        text = re.sub(re_normalize, r'\g<1>', text)
    #return text.encode('utf8')
    return text

def get_innerHTML(e):
    # TODO: this may lose some text info?
    return ''.join([etree.tostring(x) for x in list(e)])

def get_link_density(e):
    links = e.findall('.//a')
    text_length = len(get_inner_text(e))
    link_length = 0
    for link in links:
        if link.text != None:
            link_length += len(link.text)
        elif len(link) == 1 and str(link[0].tag).lower() == 'img':
            link_length += min(etree.tostring(link[0], encoding=unicode),30)
        else:
            link_length += len(get_inner_text(link))
    link_dens =  float(link_length) / (text_length or 1.0)
    if link_dens > 1:
        link_dens = 1.0
    return link_dens

def get_text_density(e):
    text_length = len(get_inner_text(e))
    ele_length = len(etree.tostring(e, encoding=unicode))
    return float(text_length) / (ele_length or 1)

def get_inner_text_conditionally(node, norm=True):
    inner_text = ''
    text_dens = get_text_density(node)
    text = get_inner_text(node, norm)
    text_len = len(text)
    link_dens = get_link_density(node)
    if not text.strip():
        return ''
    if text_dens >= 0.5:
        inner_text += '\n' + text
    elif text_len > 80 and link_dens < 0.25:
        inner_text += '\n' + text
    elif text_len < 80 and link_dens == 0:
        inner_text += '\n' + text
    return inner_text

def pre_document(doc):
    """clean the document, remove no need script, style, etc."""
    doc = doc.replace('\r', '')
    from lxml.html.clean import Cleaner
    cleaner = Cleaner(page_structure=False, links=False, forms=False, safe_attrs_only=False)
    return cleaner.clean_html(doc)

def _get_max_len_text(text_list):
    text = ''
    for txt in text_list:
        if len(txt) > len(text):
            text = txt
    return text

def get_article_title(doc):
    cur_title = ''
    orig_title = ''

    title = doc.head.find('title')
    if title is not None:
        cur_title = title.text
        orig_title = title.text

    title_candidates = []
    for x in range(1,4):
        hxs = doc.findall('.//h%d'%x)
        if hxs:
            for ele in hxs:
                text = get_inner_text(ele).strip()
                if text and len(text) > 10 and text in orig_title:
                    title_candidates.append(text)
    if title_candidates:
        return _get_max_len_text(title_candidates)

    if not cur_title:
        titles = doc.body.findall('title')
        if titles:
            cur_title = orig_title = get_inner_text(titles[0])

    if re.search(r' [\|\-] ', cur_title):
        cur_title = re.sub(r'(.*)[\|\-] .*', r'\g<1>', orig_title)
        if len(cur_title.split(' ')) < 3:
            cur_title = re.sub(r'[^\|\-]*[\|\-](.*)', r'\g<1>', orig_title)
    elif re.search(': ', cur_title):
        cur_title = re.sub(r'.*:(.*)', r'\g<1>', orig_title)
        if len(cur_title.split(' ')) < 3:
            cur_title = re.sub(r'[^:]*[:](.*)', r'\g<1>', orig_title)
    elif len(cur_title) > 150 or len(cur_title) < 15:
        hones = doc.findall('.//h1')
        if len(hones) == 1:
            cur_title = get_inner_text(hones[0])

    ## trim
    cur_title = cur_title.strip()
    if len(cur_title) <= 4:
        cur_title = orig_title

    return cur_title

def get_class_weight(e):
    negative = r'combx|comment|com-|contact|foot|footer|footnote|masthead|media|outbrain|promo|related|scroll|shoutbox|sidebar|side|aside|sponsor|shopping|tags|widget|hide|answer|copyright'
    positive = r'article|body|content|entry|hentry|main|page|pagination|post|text|blog|story'

    if not is_flag_active(FLAG_WEIGHT_CLASSES):
        return 0
    weight = 0
    # check for class name and id
    class_id = _get_class_id_string(e)
    if re.search(negative, class_id):
        weight -= 10
    if re.search(positive, class_id):
        #weight += 15
        # considering the inner text!
        inner_text = re.sub(r'\s+', '', get_inner_text(e))
        inner_len = len(inner_text)
        if inner_len >= 80:
            weight += 10
        elif inner_len >= 30:
            weight += 2

    ## give some specific tags an extra bonus
    if e.get('class','') == 'content' or e.get('id', '') == 'content':
        weight += 10
    return weight

def initialize_node(node, node_stats):
    node_stats[node] = 0
    inner_text = re.sub(r'\s+', '', get_inner_text(node))
    if len(inner_text) == 0:
        return

    tag = str(node.tag).lower()
    if tag == 'div':
        node_stats[node] += 5;
    elif tag in ['pre', 'td', 'blockquote']:
        node_stats[node] += 3;

    elif tag in ['address', 'ol', 'ul', 'dl', 'dd', 'dt','li','form']:
        node_stats[node] -= 3;
    elif tag in ['h1','h2','h3','h4','h5','h6','th']:
        node_stats[node] -= 5;
    node_stats[node] += get_class_weight(node)

def _copy_children(tree, new_node):
    """
    move all content of tree to new_node.
    only used in grab_article.
    """
    for e in list(tree):
        ## TODO: need copy a new element?
        new_node.append(e)
    if tree.text:
        new_node.text = tree.text
    return new_node

def get_nodes_to_score(body):
    noCandidates = r'copyright|sidebar|aside|side|sponsor|ad-break|pagination|pager|popup'
    unlikelyCandidates = r'combx|comment|disqus|extra|foot|header|menu|rss|shoutbox|agegate'
    MaybeCandidate = r'and|article|body|column|main|shadow'
    #divToPElements = r'<(a|blockquote|dl|div|img|ol|p|pre|table|ul)'
    divToPElements = r'<(dl|div|ol|p|pre|table|ul)'

    strip_unlikely_candidates = is_flag_active(FLAG_STRIP_UNLIKELYS)
    nodes_to_score = []
    nodes_to_remove = []
    # CAUSION: first remove the all the nodes to be removed, then iter body for nodes to be scored.
    for node in body.iter():
        tag = str(node.tag).lower()
        if tag == 'body':
            continue

        # Remove unlikely candidates
        if strip_unlikely_candidates:
            if match_node_class_id(noCandidates, node):
                nodes_to_remove.append(node)
            class_id_str = _get_class_id_string(node)
            #if re.search(unlikelyCandidates, class_id_str) and \
            #    (not re.search(MaybeCandidate, class_id_str)) and \
            if match_node_class_id(unlikelyCandidates, node) and \
                (not match_node_class_id(MaybeCandidate, node)) and \
                tag != 'body':
                # damn! some sites do use /header/ as the id of main content!
                if len(get_inner_text(node)) < 100:
                    nodes_to_remove.append(node)

    for node in nodes_to_remove:
        node.getparent().remove(node)

    for node in body.iter():
        tag = str(node.tag).lower()
        #if tag in ['p','td','pre']:
        if tag in ['p','pre', 'span']:
            nodes_to_score.append(node)
            continue

        # just add to nodes_to_score, not turn them into p's
        # avoid scoring both an element and its parent, such as td and its
        # div children
        if tag in ['div', 'td', 'ol', 'ul', 'dl']:
            inner_html = get_innerHTML(node)
            #if not re.search(divToPElements, inner_html):
            if (node.text and node.text.strip()) or not re.search(divToPElements, inner_html):
                nodes_to_score.append(node)
    return nodes_to_score

def pre_article(body):
    hidden_style = r'display:\s?none'
    nodes_to_remove = []
    nodes_with_tail = []
    for node in body.iter():
        tag = str(node.tag).lower()
        if tag == 'body':
            continue

        if tag in ['script','noscript', 'iframe', 'style', '<built-in function comment>']:
            nodes_to_remove.append(node)
            continue

        ## remove hidden elements.
        style = node.get('style', '')
        if style and re.search(hidden_style, style):
            nodes_to_remove.append(node)
            continue

        # if tag has a tail text
        if node.tail != None and node.tail.strip():
            nodes_with_tail.append(node)

    for node in nodes_to_remove:
        node.getparent().remove(node)

    for node in nodes_with_tail:
        new_node = etree.Element('p')
        new_node.text = node.tail
        node.tail = ''
        node.addnext(new_node)
        #nodes_to_score.append(new_node)

def grab_article(body, node_stats):
    pre_article(body)
    nodes_to_score = get_nodes_to_score(body)
    # loop through all paragraphs and assign a score to them based on how
    # content-y they look. Then add score to their parent node
    candidates = []
    # save number of currence of every scored node's class. if a class occurs
    # many times, then the nodes with that class may not be punished too heavy.
    # mainly for pages such as reddit, which contain many links
    class_cnt = {}
    for node in nodes_to_score:
        parent_node = node.getparent()
        grandparent_node = parent_node.getparent() if parent_node != None else None
        inner_text = get_inner_text(node)

        if parent_node is None or parent_node.tag is None:
            continue

        pclass = parent_node.get('class')
        if pclass != None:
            class_cnt[pclass] = class_cnt.get(pclass, 0) + 1

        ## if this paragraph is less than 25 chars, don't event count it
        if len(inner_text) < 25:
            continue

        ## initialize node_stats data for parent.
        try:
            node_stats[parent_node]
        except KeyError:
            initialize_node(parent_node, node_stats)
            candidates.append(parent_node)

        ## initialize node_stats data for grandparent
        if grandparent_node != None:
            gpclass = grandparent_node.get('class')
            if gpclass != None:
                class_cnt[gpclass] = class_cnt.get(gpclass, 0) + 1
            try:
                node_stats[grandparent_node]
            except KeyError:
                initialize_node(grandparent_node, node_stats)
                candidates.append(grandparent_node)

        content_score = 0
        # Add a point for the paragraph itself as a base.
        ## if it has no inner text, then do not give a base score
        if inner_text:
            content_score += 1

        # Add points for any commas within this paragraph
        content_score += len(inner_text.split(','))
        ## for Chinese chars!
        content_score += len(inner_text.split(u'，'))

        # For every 100 characters, add another point. Up to 3 points.
        content_score += min(len(inner_text) / 100, 3)

        # add the score to the parent, and the grandparent gets half
        #node_stats[parent_node] += content_score * 0.9
        node_stats[parent_node] += content_score

        if grandparent_node != None:
            node_stats[grandparent_node] += float(content_score) / 2

    # loop through all of the possible candidates nodes to find the one with
    # the highest score
    top_candidate = None
    for cc in candidates:
        #node_stats[cc] *= (1 - get_link_density(cc))
        node_stats[cc] *= max([(1 - get_link_density(cc)), 0.4])
        ccnt = cc.get('class')!=None and class_cnt.get(cc.get('class'), 0)
        """
        # not suitable for slashdot, whose text blocks are in different class
        # names
        if ccnt >= 10:
            node_stats[cc] *= 1.0
        elif ccnt >=3:
            node_stats[cc] *= max([(1 - get_link_density(cc)), 0.5])
        else:
            node_stats[cc] *= (1 - get_link_density(cc))
        """
        #text_density = get_text_density(cc)
        #node_stats[cc] *= text_density

        if top_candidate is None or node_stats[cc] > node_stats[top_candidate]:
            top_candidate = cc

    # if have no top_candidate, just use the body
    if top_candidate is None or str(top_candidate.tag).lower() == 'body':
        top_candidate = etree.Element('div')
        _copy_children(body, top_candidate)
        body.clear()
        body.append(top_candidate)
        initialize_node(top_candidate, node_stats)

    ## for forums, get all the nodes that have the same class with top_candidate.
    ## this part does not alter elements in body, otherwise the article_content
    ## part will not work properly.
    forum_content = etree.Element('div')
    text_class = top_candidate.get('class') or (top_candidate.getparent()!=None and top_candidate.getparent().get(
'class'))
    if text_class:
        ## may be more than one classes!
        tag = str(top_candidate.tag).lower()
        class_list = text_class.split()
        max_text = ''
        for cc in class_list:
            cc = cc.strip()
            #similar_nodes = body.findall('.//*[@class="%s"]' % cc)
            find = etree.XPath(".//%s[re:test(@class, '(^|(.* ))%s($|( .*))', 'i')]" % (tag,cc), namespaces={'re':"http://exslt.org/regular-expressions"})
            similar_nodes = find(body)

            if len(similar_nodes) > 1:
                forum_text = ''
                for node in similar_nodes:
                    forum_text += '\n' + get_inner_text(node, False)
                    #forum_text += '\n' + get_inner_text_conditionally(node, False)
                if len(forum_text) > len(max_text):
                    max_text = forum_text
        forum_content.text = max_text

    # look top_candidate's siblings for content that might also be related.
    article_content = etree.Element('div')

    sibling_threshold = max(10, node_stats[top_candidate] * 0.2)
    top_candidate_parent = top_candidate.getparent()
    if top_candidate_parent is not None:
        sibling_nodes = list(top_candidate_parent)
    else:
        sibling_nodes = []
    #if str(top_candidate_parent.tag).lower() == 'tr':
    #    sibling_nodes = list(top_candidate_parent.getparent().findall('.//td'))

    for sibling in sibling_nodes:
        append = False
        tag = str(sibling.tag).lower()

        if sibling == top_candidate:
            append = True

        bonus = 0
        # give a bonus if sibling node and top candidate have the same class
        if sibling.get('class') == top_candidate.get('class') and \
                top_candidate.get('class', '') != '':
            bonus += node_stats[top_candidate] * 0.2

        if get_text_density(sibling) > 0.4 and len(get_inner_text(sibling)) > 80:
            bonus += node_stats[top_candidate] * 0.3

        try:
            if node_stats[sibling] + bonus >= sibling_threshold:
                append = True
        except KeyError:
            pass

        if tag == 'p':
            link_density = get_link_density(sibling)
            node_content = get_inner_text(sibling)
            node_len = len(node_content)

            if node_len > 80 and link_density < 0.25:
                append = True
            elif node_len < 80 and link_density == 0 and re.search(r'(\.|。)( |$)', node_content):
                append = True

        if append:
            node_to_append = None
            if tag != 'div' and tag != 'p':
                # We have a node that isn't a common block level element,
                # like a form or td tag. Turn it into a div so it doesn't
                # get filtered out later by accident.
                node_to_append = etree.Element('div')
                _copy_children(sibling, node_to_append)
                if sibling.get('id'):
                    node_to_append.set('id', sibling.get('id'))
            else:
                node_to_append = sibling
            node_to_append.set('class', '')
            article_content.append(node_to_append)

    ## TODO: need to re-run ??
    article_content_len = len(get_inner_text(article_content, False))
    if forum_content.text and len(forum_content.text) > article_content_len:
        return forum_content

    """
    if article_content_len < 150:
        body = body_cache_html.find('body')
        if is_flag_active(FLAG_STRIP_UNLIKELYS):
            remove_flag(FLAG_STRIP_UNLIKELYS)
            grab_article(body)
        elif is_flag_active(FLAG_WEIGHT_CLASSES):
            remove_flag(FLAG_WEIGHT_CLASSES)
            grab_article(body)
        else:
            return body
    """
    return article_content
