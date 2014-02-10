# To change this template, choose Tools | Templates
# and open the template in the editor.
import os.path
import setpath
import sys
import imp
from lib.dsv import writer
import gzip
from lib.ziputils import ZipIter
import functions
from lib.vtoutgtable import vtoutpugtformat
import lib.inoutparsing
import os
import apsw
from collections import defaultdict
import json
from itertools import izip
import itertools
import marshal as marshal
import cPickle
import pickle
import setpath
import vtbase
import functions
import struct
from array import array
import vtbase
import functions
import apsw
import os
import sys
import gc
#import marshal
import gc
import re
import zlib
### Classic stream iterator
registered=True
BLOCK_SIZE = 32768000


class UnionAllRC(vtbase.VT):


    def VTiter(self, *args,**formatArgs):
        largs, dictargs = self.full_parse(args)
        where = None
        mode = 'row'

        if 'file' in dictargs:
            where=dictargs['file']
        else:
            raise functions.OperatorError(__name__.rsplit('.')[-1],"No destination provided")
        col = 0

        if 'cols' in dictargs:
            a = re.split(' |,| , |, | ,' , dictargs['cols'])
            column = [x for x in a if x != '']
        else:
            col = 1
        start = 0
        end = sys.maxint-1
        if 'start' in dictargs:
            start = int(dictargs['start'])
        if 'end' in dictargs:
            end = int(dictargs['end'])

        fullpath = str(os.path.abspath(os.path.expandvars(os.path.expanduser(os.path.normcase(where)))))
        fileIterlist = []
        for x in xrange(start,end+1):
            try:
                fileIterlist.append(open(fullpath+"."+str(x), "rb"))
            except:
                break

        if fileIterlist == []:
            try:
                fileIterlist = [open(where, "rb")]
            except :
                raise  functions.OperatorError(__name__.rsplit('.')[-1],"No such file")

        for filenum,fileObject in enumerate(fileIterlist):
            schema = marshal.load(fileObject)
            colnum = len(schema)
            ENDFILE = 0
            if filenum == 0:
                yield schema

            while True:
                row=0
                d = 0
                ind = [0 for _ in xrange(colnum+2)]

                if ENDFILE==1:
                    try:
                        newschema=marshal.load(fileObject)
                        ENDFILE=0
                    except EOFError:
                        break

                for i in xrange(colnum+2):
                    ind[i] = struct.unpack('L',fileObject.read(8))

                if ind[colnum+1][0] == 1:
                    ENDFILE = 1

                d2 = [marshal.loads(zlib.decompress(fileObject.read(ind[col+1][0]-ind[col][0])))
                      for col in xrange(colnum)]

                rowcount = len(d2[0])
                for row in xrange(rowcount):
                    yield tuple(d2[col][row] for col in xrange(colnum))

        try:
            for fileObject in fileIterlist:
                fileObject.close()
        except NameError:
            pass


def Source():
    return vtbase.VTGenerator(UnionAllRC)

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


