import os
import string 
from collections import OrderedDict

class DictTree(object):
    """
    A tree as an ordered dictionary (root), 
    extended by embedding other ordered dictionaries.
    Fetches an item by a uri string that is a sequence 
    of dict keys, connected by '.'s.
    """

    def __init__(self,data={}):
        super(DictTree,self).__init__()
        self._root = OrderedDict()
        if isinstance(data,dict):
            self._root = OrderedDict(data)
        self.bad_chars = string.punctuation 
        self.bad_chars = self.bad_chars.replace('_','')
        self.bad_chars = self.bad_chars.replace('-','')
        self.bad_chars = self.bad_chars.replace('.','')
        self.space_chars = [' ','\t','\n',os.linesep]

    def __getitem__(self,uri):
        return self.get_from_uri(uri)

    def __setitem__(self,uri,val):
        self.set_uri(uri,val)

    def __len__(self):
        return self.n_items()
 
    def n_items(self,root_uri=''):
        """
        Get the total number of data items in the tree.
        Only nodes containing data (i.e. end nodes) are counted.
        Nodes referencing containers, for example, are not counted. 
        """
        if root_uri:
            itm = self.get_from_uri(root_uri)
            prefix = root_uri + '.'
        else:
            itm = self._root
            prefix = ''
        #elif isinstance(itm,list):
        #    return sum([self.n_items(root_uri+'.'+str(i)) for i in range(len(itm))])
        if isinstance(itm,dict):
            return sum([self.n_items(prefix+k) for k in itm.keys()])
        else:
            # terminal node: return 1
            return 1 

    def delete_uri(self,uri=''):
        """
        Delete the given uri, i.e., 
        remove the corresponding key from the embedded dict.
        """
        try:
            itm = self._root
            if '.' in uri:
                itm = self.get_from_uri(uri[:uri.rfind('.')])
            path = uri.split('.')
            k = path[-1]
            if k:
                itm.pop(k)
        except Exception as ex:
            msg = str('\n[{}] Encountered an error while trying to delete uri {}: \n'
            .format(__name__,uri))
            ex.message = msg + ex.message
            raise ex

    def set_uri(self,uri='',val=None):
        """
        Set the data at the given uri to provided value val.
        """
        try:
            itm = self._root
            if '.' in uri:
                itm = self.get_from_uri(uri[:uri.rfind('.')])
            k = uri.split('.')[-1]
            if k:
                itm[k] = val
        except Exception as ex:
            msg = str('\n[{}] Encountered an error while trying to set uri {} to val {}: \n'
            .format(__name__,uri,val))
            ex.message = msg + ex.message
            raise ex

    def get_from_uri(self,uri=''):
        """
        Return the data stored at uri.
        """
        try:
            path = uri.split('.')
            itm = self._root 
            for k in path[:-1]:
                # TODO: Handle list item retrieval better
                if isinstance(itm,list):
                    itm = itm[int(k)]
                else:
                    itm = itm[k]
            k = path[-1]
            if k == '':
                return itm 
            elif k is not None:
                if isinstance(itm,list):
                    return itm[int(k)]
                else:
                    return itm[k]
        except Exception as ex:
            msg = str('[{}] Encountered an error while fetching uri {}: \n'
            .format(__name__,uri) + ex.message)
            raise KeyError(msg) 

    def list_child_tags(self,parent_uri=''):
        if parent_uri:
            p_itm = self.get_from_uri(parent_uri)
        else:
            p_itm = self._root
        if isinstance(p_itm,dict):
            return p_itm.keys()

    def list_uris(self,root_uri=''):
        if root_uri:
            itm = self.get_from_uri(root_uri)
            l = [root_uri]
            prefix = root_uri+'.'
        else:
            itm = self._root
            l = []
            prefix = ''
        if isinstance(itm,dict):
            for k,x in itm.items():
                l = l + self.list_uris(prefix+k)
        return l
            
    def is_uri_valid(self,uri):
        """
        Check for validity of a uri. 
        Uris may contain upper case letters, lower case letters, 
        numbers, dashes (-), and underscores (_). 
        Periods (.) are used as delimiters between tags in the uri.
        Any whitespace or any character in the string.punctuation library
        (other than -, _, or .) results in an invalid uri.
        """
        #if parent is None:
        #    parent = self.root_index()
        if (any(map(lambda s: s in uri,self.space_chars))
            or any(map(lambda s: s in uri,self.bad_chars))):
            return False 
        return True 

    def is_tag_valid(self,tag):
        """
        Check for validity of a tag.
        The conditions for a valid tag are the same as for a valid uri,
        except that a tag should not contain period (.) characters.
        """
        if '.' in tag:
            return False 
        else:
            return self.is_uri_valid(tag)

    def is_uri_unique(self,uri):
        """
        Check for uniqueness of a uri. 
        """
        #if parent is None:
        #    parent = self.root_index()
        if uri in self.list_uris():
            return False 
        else:
            return True 

    def uri_error(self,uri):
        """Provide a human-readable error message for bad uris."""
        if not uri:
            err_msg = 'uri is blank.'
        elif any(map(lambda s: s in uri,self.space_chars)):
            err_msg = 'uri contains whitespace.'
        elif any(map(lambda s: s in uri,self.bad_chars)):
            err_msg = 'uri contains special characters.'
        else:
            err_msg = 'Unforeseen uri error.'
        return str('uri error for {}: \n{}\n'.format(uri,err_msg))

    def tag_error(self,tag):
        """Provide a human-readable error message for bad tags."""
        if '.' in tag:
            return 'tag error for {}: \ntag contains a period (.)\n'.format(tag)
        else:
            return self.uri_error(tag)

    def contains_uri(self,uri):
        """Returns whether or not input uri points to an item in this tree."""
        return uri in self.list_uris()
        #if not uri:
        #    return False
        #path = uri.split('.')
        #p_idx = QtCore.QModelIndex()
        #for itemuri in path:
        #    try:
        #        row = self.list_child_tags(p_idx).index(itemuri)
        #    except ValueError as ex:
        #        return False
        #    idx = self.index(row,0,p_idx)
        #    p_idx = idx
        #return True

    def make_unique_uri(self,prefix):
        """
        Generate the next unique uri from prefix by appending '_x' to it, 
        where x is a minimal nonnegative integer.
        """
        suffix = 0
        gooduri = False
        urilist = self.list_uris()
        while not gooduri:
            testuri = prefix+'_{}'.format(suffix)
            if not testuri in urilist: 
                gooduri = True
            else:
                suffix += 1
        return testuri 

    def print_tree(self,rowprefix='',root_uri=''):
        if root_uri:
            itm = self.get_from_uri(root_uri)
        else:
            itm = self._root
        if isinstance(itm,dict):
            tree_string = '\n'
            for k,x in itm.items():
                x_tree = self.print_tree(rowprefix+'\t',root_uri+'.'+k)
                tree_string = tree_string+rowprefix+'{}: {}\n'.format(k,x_tree)
        #elif isinstance(itm,list):
        #    tree_string = '\n'
        #    for i,x in zip(range(len(itm)),itm):
        #        x_tree = self.print_tree(rowprefix+'\t',root_uri+'.'+str(i))
        #        tree_string = tree_string+rowprefix+'{}: {}\n'.format(i,x_tree)
        else:
            return '{}'.format(itm)
        return tree_string

#        if parent.isValid():
#            itm = self.get_item(parent)
#            tree_string = tree_string+rowprefix+str(itm.data)+'\n'
#            for j in range(itm.n_children()):
#                tree_string = tree_string + self.print_tree(rowprefix+'\t',self.index(j,0,parent))
#                l.append(root_uri+'.'+str(i))
#                l = l + self.list_uris(root_uri+'.'+str(i))
#
            