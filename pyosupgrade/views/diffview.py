from difflib import HtmlDiff
from flask import request, render_template
from pymongo import MongoClient
from lxml import etree

mongo = MongoClient("mongo")


def get_command_list(text):
    """
    find XML encoded command list from pre/post verification output
    :param text: str
    :return: list of commands
    """
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(text, parser)
        # after_xml = etree.fromstring(obj.after)
    commands = root.xpath("//command")
    command_list = list()
    for c in commands:
        command_list.append(c.attrib.get('cmd'))
    return command_list


def get_command_table(before_text, after_text, show_command):
    """
    Returns an HTML table of the differences between a specific command on all devices

    :param before_xml:
    :param after_xml:
    :param show_command:
    :return:
    """
    parser = etree.XMLParser(recover=True)
    before_xml = etree.fromstring(before_text, parser)
    after_xml = etree.fromstring(after_text, parser)
    xpath_query = "//command[@cmd='{}']/text()".format(show_command)
    before_command_lines = list()
    after_command_lines = list()

    for device in before_xml.xpath(xpath_query):
        print device.split('\n')
        before_command_lines = before_command_lines + device.split('\n')
    for device in after_xml.xpath(xpath_query):
        after_command_lines = after_command_lines + device.split('\n')
    diff = HtmlDiffer(wrapcolumn=120)
    table = diff.make_table(before_command_lines, after_command_lines)
    return table


class HtmlDiffer(HtmlDiff):
    # This is dumb but HTMLDiff doesn't provide a way to set the text for <a> tags so we
    # perform a little hackery
    def _convert_flags(self,fromlist,tolist,flaglist,context,numlines):
        """Makes list of "next" links"""

        # all anchor names will be generated using the unique "to" prefix
        toprefix = self._prefix[1]

        # process change flags, generating middle column of next anchors/links
        next_id = ['']*len(flaglist)
        next_href = ['']*len(flaglist)
        num_chg, in_change = 0, False
        last = 0
        for i,flag in enumerate(flaglist):
            if flag:
                if not in_change:
                    in_change = True
                    last = i
                    # at the beginning of a change, drop an anchor a few lines
                    # (the context lines) before the change for the previous
                    # link
                    i = max([0,i-numlines])
                    next_id[i] = ' id="difflib_chg_%s_%d"' % (toprefix,num_chg)
                    # at the beginning of a change, drop a link to the next
                    # change
                    num_chg += 1
                    next_href[last] = '<a href="#difflib_chg_%s_%d">next diff</a>' % (
                         toprefix,num_chg)
            else:
                in_change = False
        # check for cases where there is no content to avoid exceptions
        if not flaglist:
            flaglist = [False]
            next_id = ['']
            next_href = ['']
            last = 0
            if context:
                fromlist = ['<td></td><td>&nbsp;No Differences Found&nbsp;</td>']
                tolist = fromlist
            else:
                fromlist = tolist = ['<td></td><td>&nbsp;Empty File&nbsp;</td>']
        # if not a change on first line, drop a link
        if not flaglist[0]:
            next_href[0] = '<a href="#difflib_chg_%s_0">first diff</a>' % toprefix
        # redo the last link to link to the top
        next_href[last] = '<a href="#difflib_chg_%s_top">go to top</a>' % (toprefix)

        return fromlist,tolist,flaglist,next_href,next_id


def diff(log1, log2):
    """
    Displays the difference of two files

    :param log1:
    :param log2:
    :return:
    """
    show_command = request.args.get("show_command", None)

    # if we receive a URL we only need the id
    if '/logbin/embedded/' in log1:
        log1 =log1.split('/logbin/embedded/')[1]
    if '/logbin/embedded/' in log2:
        log2 =log2.split('/logbin/embedded/')[1]


    log1doc = mongo.db.logbin.find_one({"id": log1}, {"_id": 0})['text']
    log2doc = mongo.db.logbin.find_one({"id": log2}, {"_id": 0})['text']

    # Get list of xml encoded commands
    try:
        commands = get_command_list(log1doc)
    except Exception:
        commands = None

    # we need list of lines for HtmlDiffer
    log1lines = log1doc.split('\n')
    log2lines = log2doc.split('\n')
    print log1lines
    print log2lines

    diff = HtmlDiffer(wrapcolumn=80)
    if show_command is not None:
        table = get_command_table(log1doc, log2doc, show_command)
    else:
        table = diff.make_table(log1lines, log2lines)
    if commands:
        return render_template('diff-view.html', table=table, commands=commands)
    else:
        return render_template('diff-view.html', table=table)