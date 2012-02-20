"""
.. function:: file(location, [formatting options])

Opens and returns a file or url as a table. The file's format is defined through
named options. *location* is defined through a URL, or a regular filename, can be given also as
the named parameter *url* or *file*. If no named parameters are given the returned table has one column
with each line of resource as a row or it assumes the dialect from the file ending (Files ending in .tsv or .csv are automatically
recognized with the corresponding dialect).

:Returned table schema:
    Columns are automatically named as *C1, C2...* or if header is set, columns are named by the resource first line value, and have the type *text*

Formatting options:

:encoding:

    A standar encoding name. (`List of encodings <http://docs.python.org/library/codecs.html#standard-encodings>`_)

:compression: *t/f*

    Default is *f* (False)

:compressiontype: *zip/gzip*

    Default is *zip*

Formatting options for CSV file types:

:dialect: *tsv/csv*

    Formats field as tab/comma separated values with minimal quoting

:header: *t/f*

    Set the column names of the returned table

:delimiter:

    A string used to separate fields. It defaults to ','

:doublequote: *t/f*

    Controls how instances of quotechar appearing inside a field should be themselves be quoted. When True, the character is doubled. When False, the escapechar is used as a prefix to the quotechar. It defaults to True.
    On output, if doublequote is False and no escapechar is set, Error is raised if a quotechar is found in a field

:escapechar:

    A one-character string used by the writer to escape the delimiter if quoting is set to QUOTE_NONE and the quotechar if doublequote is False. On reading, the escapechar removes any special meaning from the following character. It defaults to None, which disables escaping

:lineterminator:

    The string used to terminate lines produced by the writer. It defaults to '\\\\r\\\\n'

:quotechar:

    A one-character string used to quote fields containing special characters, such as the delimiter or quotechar, or which contain new-line characters. It defaults to '"'.

:quoting:

    Controls when quotes should be generated by the writer and recognised by the reader. It can take on any of the QUOTE_* constants and defaults to QUOTE_MINIMAL.
    Possible values are QUOTE_ALL, QUOTE_NONE, QUOTE_MINIMAL, QUOTE_NONNUMERIC

:skipinitialspace: *t/f*

    When True, whitespace immediately following the delimiter is ignored. The default is False

Examples::
  
    >>> sql("select * from (file file:testing/colpref.csv dialect:csv) limit 3;")
    C1     | C2    | C3         | C4
    --------------------------------------
    userid | colid | preference | usertype
    agr    |       | 6617580.0  | agr
    agr    | a0037 | 2659050.0  | agr
    >>> sql("select * from (file file:testing/colpref.csv dialect:csv header:t) limit 3")
    userid | colid | preference | usertype
    --------------------------------------
    agr    |       | 6617580.0  | agr
    agr    | a0037 | 2659050.0  | agr
    agr    | a0086 | 634130.0   | agr
    >>> sql("select * from (file file:testing/colpref.zip header:t dialect:csv compression:t) limit 3;")
    userid | colid | preference | usertype
    --------------------------------------
    agr    |       | 6617580.0  | agr
    agr    | a0037 | 2659050.0  | agr
    agr    | a0086 | 634130.0   | agr
    >>> sql("select * from (file 'testing/colpref.tsv' delimiter:| ) limit 3;")
    C1  | C2    | C3        | C4
    -----------------------------
    agr |       | 6617580.0 | agr
    agr | a0037 | 2659050.0 | agr
    agr | a0086 | 634130.0  | agr
    >>> sql("select * from (file 'testing/colpref.tsv.gz' delimiter:| compression:t compressiontype:gzip) limit 3;")
    C1  | C2    | C3        | C4
    -----------------------------
    agr |       | 6617580.0 | agr
    agr | a0037 | 2659050.0 | agr
    agr | a0086 | 634130.0  | agr
    >>> sql("select * from file('http://sites.google.com/site/stats202/data/test_data.csv?attredirects=0') limit 10;")
    C1
    -----------------
    Age,Number,Start
    middle,5,10
    young,2,17
    old,10,6
    young,2,17
    old,4,15
    middle,5,15
    young,3,13
    old,5,8
    young,7,9
    >>> sql("select * from file('file:testing/GeoIPCountryCSV.zip','compression:t','dialect:csv') limit 4")
    C1          | C2           | C3       | C4       | C5 | C6
    ----------------------------------------------------------------------
    2.6.190.56  | 2.6.190.63   | 33996344 | 33996351 | GB | United Kingdom
    3.0.0.0     | 4.17.135.31  | 50331648 | 68257567 | US | United States
    4.17.135.32 | 4.17.135.63  | 68257568 | 68257599 | CA | Canada
    4.17.135.64 | 4.17.142.255 | 68257600 | 68259583 | US | United States
"""

registered=True
external_stream=True

from vtiterable import SourceVT
from lib.dsv import reader                
import lib.gzip32 as gzip
import urllib2
import urlparse
import functions
from lib.iterutils import peekable
from lib.ziputils import ZipIter
import codecs

import lib.inoutparsing
from functions.conf import domainExtraHeaders

csvkeywordparams=set(['delimiter','doublequote','escapechar','lineterminator','quotechar','quoting','skipinitialspace','dialect'])

def nullify(iterlist):
    for lst in iterlist:
        nlst=[]
        for el in lst:
            if el.upper()=='NULL':
                nlst+=[None]
            else:
                nlst+=[el]
        yield nlst

class FileCursor:
    def __init__(self,filename,isurl,compressiontype,compression,hasheader,first,namelist,extraurlheaders,**rest):
        self.encoding='utf-8'
        
        if 'encoding' in rest:
            self.encoding=rest['encoding']
            del rest['encoding']

        self.nonames=first
        for el in rest:
            if el not in csvkeywordparams:
                raise functions.OperatorError(__name__.rsplit('.')[-1],"Invalid parameter %s" %(el))

        gzipcompressed=False
        try:
            if compression and compressiontype=='zip':
                self.fileiter=ZipIter(filename,"r")
            elif not isurl:
                pathname=filename.strip()
                self.fileiter=codecs.open(filename, encoding = self.encoding)
            else:
                pathname=urlparse.urlparse(filename)[2]
                req=urllib2.Request(filename,None,extraurlheaders)
                hreq=urllib2.urlopen(req)
                if [1 for x,y in hreq.headers.items() if x.lower() in ('content-encoding', 'content-type') and y.lower().find('gzip')!=-1]:
                    gzipcompressed=True
                self.fileiter=hreq

            if pathname.endswith('.gz') or pathname.endswith('.gzip'):
                gzipcompressed=True

            if compression and compressiontype=='gz':
                gzipcompressed=True

            if gzipcompressed:
                self.fileiter=gzip.GzipFile(fileobj=self.fileiter)

        except Exception,e:
            raise functions.OperatorError(__name__.rsplit('.')[-1],e)

        if filename.endswith('.csv'):
            rest['dialect']=lib.inoutparsing.defaultcsv()
        if filename.endswith('.tsv'):
            rest['dialect']=lib.inoutparsing.tsv()

        if hasheader or len(rest)>0: #if at least one csv argument default dialect is csv else line
            if 'dialect' not in rest:
                rest['dialect']=lib.inoutparsing.defaultcsv()
            if first and not hasheader:
                self.iter=peekable(nullify(reader(self.fileiter,encoding=self.encoding,**rest)))
                sample=self.iter.peek()
            else: ###not first or header
                self.iter=nullify(reader(self.fileiter, encoding=self.encoding, **rest))
                if hasheader:
                    sample=self.iter.next()
            if first:
                if hasheader:
                    for i in sample:
                        namelist.append(i)
                else:
                    for i in xrange(1,len(sample)+1):
                        namelist.append("C"+str(i))
        else: #### Default read lines
            self.iter=self.fileiter
            namelist.append("C1")
            
    def __iter__(self):
        return self
    def next(self):
        try:
            return (self.iter.next(),)
        except UnicodeDecodeError, e:
            raise functions.OperatorError(__name__.rsplit('.')[-1], unicode(e)+"\nFile is not %s encoded" %(self.encoding))
    def close(self):
        self.fileiter.close()
        
class FileVT:
    def __init__(self,envdict,largs,dictargs): #DO NOT DO ANYTHING HEAVY
        self.largs=largs
        self.envdict=envdict
        self.dictargs=dictargs
        self.nonames=True
        self.names=[]
        self.destroyfiles=[]
        self.inoutargs={}
        self.extraheader={}
        
    def getdescription(self):
        if not self.names:
            raise functions.OperatorError(__name__.rsplit('.')[-1],"VTable getdescription called before initiliazation")
        self.nonames=False
        return [(i,'text') for i in self.names]
    def open(self):
        if self.nonames:
            try:
                inoutargs=lib.inoutparsing.inoutargsparse(self.largs,self.dictargs)
            except lib.inoutparsing.InputsError:
                raise functions.OperatorError(__name__.rsplit('.')[-1]," One source input is required")
            if not inoutargs['filename']:
                raise functions.OperatorError(__name__.rsplit('.')[-1],"No input provided")
            
            if inoutargs['url']:
                for domain in domainExtraHeaders:
                    if domain in inoutargs['filename']:
                        self.extraheader=domainExtraHeaders[domain]
                        break
                if 'User-Agent' not in self.extraheader:
                    self.extraheader['User-Agent']='Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
            if inoutargs['url'] and inoutargs['compression'] and inoutargs['compressiontype']=='zip':
                inoutargs['filename']=lib.inoutparsing.cacheurl(inoutargs['filename'],self.extraheader)
                self.destroyfiles=[inoutargs['filename']]
                inoutargs['url']=False
            self.inoutargs=inoutargs
        
        return FileCursor(self.inoutargs['filename'],self.inoutargs['url'],self.inoutargs['compressiontype'],self.inoutargs['compression'],self.inoutargs['header'],self.nonames,self.names,self.extraheader,**self.dictargs)
    def destroy(self):
        import os
        for f in self.destroyfiles:
            os.remove(f)

def Source():
    global boolargs, nonstringargs
    return SourceVT(FileVT, lib.inoutparsing.boolargs+['header','compression'], lib.inoutparsing.nonstringargs, lib.inoutparsing.needsescape)


if not ('.' in __name__):
    """
    This is needed to be able to test the function, put it at the end of every
    new function you create
    """
    import sys
    import setpath
    from functions import *
    testfunction()
    if __name__ == "__main__":
        reload(sys)
        sys.setdefaultencoding('utf-8')
        import doctest
        doctest.testmod()