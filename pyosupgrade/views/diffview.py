from difflib import HtmlDiff
from flask import request, render_template
from pymongo import MongoClient

mongo = MongoClient("mongo")



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
    # if we receive a URL we only need the id
    if '/logbin/embedded/' in log1:
        log1 =log1.split('/logbin/embedded/')[1]
    if '/logbin/embedded/' in log2:
        log2 =log2.split('/logbin/embedded/')[1]

    log1lines = mongo.db.logbin.find_one({"id": log1}, {"_id": 0})['text'].split('\n')
    log2lines = mongo.db.logbin.find_one({"id": log2}, {"_id": 0})['text'].split('\n')

    print log1lines
    print log2lines

    diff = HtmlDiffer(wrapcolumn=120)
    table = diff.make_table(log1lines, log2lines)
    return render_template('diff-view.html', table=table)