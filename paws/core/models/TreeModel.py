from collections import OrderedDict

from .TreeItem import TreeItem
from .DictTree import DictTree

class TreeModel(object):
    """
    This class indexes a DictTree with a set of TreeItems.
    TreeItems keep track of their lineage in the DictTree,
    and can be modified for additional functionality
    in subclasses of TreeModel by adding TreeItem.flags.
    """

    def __init__(self):#,dicttree=DictTree()):
        super(TreeModel,self).__init__()
        # a TreeItem with no parent is the root of the tree
        self._root_item = TreeItem(None,'ROOT')
        # the tree data is all stored in a DictTree. 
        self._tree = DictTree()
        #if isinstance(dicttree,DictTree):
        #    for k in dicttree.list_child_tags():
        #        self.set_item(k,dicttree[k])
        #    self._tree = dicttree

    def __getitem__(self,uri):
        return self._tree.get_from_uri(uri)

    def __setitem__(self,uri,val):
        self._tree.set_uri(uri,val)
    
    #def __len__(self):
    #    return self.n_items()
 
    #def list_child_tags(self,parent_uri=''):
    #    return self._tree.list_child_tags(parent_uri)

    def n_children(self,parent_uri=''):
        itm = self.get_from_uri(parent_uri)
        return itm.n_children()

    def set_item(self,itm_uri,itm_data=None):
        if '.' in itm_uri:
            #parent_uri = itm_uri[:itm_uri.rfind('.')]
            parent_uri = itm_uri[:itm_uri.rfind('.')]
            if self.contains_uri(parent_uri):
                parent_itm = self.get_from_uri(parent_uri)
            else:
                parent_itm = self.build_to_uri(parent_uri)
            itm_tag = itm_uri.split('.')[-1]
        else:
            parent_itm = self._root_item
            itm_tag = itm_uri
        # add TreeItems to index the new TreeModel content 
        treedata = self.build_tree(itm_data)
        self.tree_update(parent_itm,itm_tag,treedata)
        # store the data 
        self._tree.set_uri(itm_uri,itm_data)

    def remove_item(self,itm_uri):
        itm = self.get_from_uri(itm_uri)
        self._tree.delete_uri(itm_uri)
        # remove the corresponding subtree or TreeItem.
        parent_itm = itm.parent 
        child_keys = [c.tag for c in parent_itm.children]
        rm_row = child_keys.index(itm.tag)
        parent_itm.children.pop(rm_row)

    def tree_update(self,parent_itm,itm_tag,itm_data):
        """
        Update the tree structure around parent_itm.children[itm_tag],
        such that TreeItems get built 
        to index all of the items in itm_data 
        that are supported by self.build_tree().
        """
        child_keys = [c.tag for c in parent_itm.children]
        if itm_tag in child_keys:
            # Find the row of existing itm_tag under parent,
            itm_row = child_keys.index(itm_tag)
            itm = parent_itm.children[itm_row]
        else:
            # Else, put a new TreeItem at the end row
            itm_row = parent_itm.n_children()
            itm = self.create_tree_item(parent_itm,itm_tag)
            parent_itm.children.insert(itm_row,itm)
        # If needed, recurse on itm_data
        # Assume build_tree was called on itm_data,
        # so only need to check for dict.
        if isinstance(itm_data,dict):
            for tag,val in itm_data.items():
                self.tree_update(itm,tag,val)

    def build_tree(self,x):
        """
        TreeModel.build_tree is called on some object x
        before x is stored in the tree.
        For subclasses of TreeModel to build tree data
        for data types other than dicts and lists,
        build_tree should be reimplemented.
        If data types other than dicts and lists have child items 
        that should be accessible by TreeModel uris,
        they should implement __getitem__(tag).
        """
        if isinstance(x,dict):
            d = OrderedDict(x)
            for k,v in d.items():
                d[k] = self.build_tree(v)
            return d
        elif isinstance(x,list):
            d = OrderedDict(zip([str(i) for i in range(len(x))],x)) 
            for k,v in d.items():
                d[k] = self.build_tree(v)
            return d
        else:
            return x

    def build_to_uri(self,uri=''):
        """ 
        If the tree does not contain the input uri,
        Fill the tree out with empty TreeItems 
        until an empty TreeItem exists at the given uri. 
        """
        try:
            itm = self._root_item 
            if '.' in uri:
                parent_uri = uri[:uri.rfind('.')]
                if self.contains_uri(parent_uri):
                    itm = self.get_from_uri(parent_uri)
                else:
                    itm = self.build_to_uri(parent_uri)
            k = uri.split('.')[-1]
            if k == '':
                return itm 
            elif k is not None:
                newdict = OrderedDict()
                self.tree_update(itm,k,newdict)
                return self.get_from_uri(uri) 
        except Exception as ex:
            msg = str('[{}] Encountered an error while trying to build uri {}: \n'
            .format(__name__,uri) + ex.message)
            raise KeyError(msg) 

    def get_from_uri(self,uri):
        try:
            path = uri.split('.')
            itm = self._root_item
            for k in path[:-1]:
                child_keys = [c.tag for c in itm.children]
                itm = itm.children[child_keys.index(k)]
            k = path[-1]
            if k:
                child_keys = [c.tag for c in itm.children]
                return itm.children[child_keys.index(k)]
            elif k == '':
                return itm 
        except Exception as ex:
            msg = '\n[{}] Encountered an error while fetching uri {}\n'.format(__name__,uri)
            ex.message = msg + ex.message
            raise ex

    def get_data_from_uri(self,uri):
        return self._tree.get_from_uri(uri)

    #def n_items(self):
    #    return self._tree.n_items()

    def root_tags(self):
        return self._tree.root_keys()

    def tag_error(self,tag):
        return self._tree.tag_error(tag)

    def is_uri_valid(self,uri):
        return self._tree.is_uri_valid(uri)

    def is_tag_valid(self,tag):
        return self._tree.is_tag_valid(tag)

    def make_unique_uri(self,prefix):
        return self._tree.make_unique_uri(prefix)

    def contains_uri(self,uri):
        return self._tree.contains_uri(uri)

    def list_uris(self,root_uri=''):
        return self._tree.list_uris(root_uri)

    def get_data_from_idx(self,idx):
        uri = self.build_uri(idx)
        return self.get_data_from_uri(uri)

    def build_uri(self,itm):
        """
        Build a URI for TreeItem itm by combining the tags 
        of the lineage of itm, with '.' as a delimiter.
        """
        if itm == self._root_item:
            return ''
        else:
            uri = itm.tag
            while not itm.parent == self._root_item:
                itm = itm.parent
                uri = itm.tag+"."+uri
            return uri

    def create_tree_item(self,parent_itm,itm_tag):
        """
        Build a TreeItem for use in this tree.
        Reimplement create_tree_item() in subclasses of TreeModel
        to add features to TreeItems, such as default values for TreeItem.flags.
        TreeModel implementation returns TreeItem(parent_itm,itm_tag).
        """
        return TreeItem(parent_itm,itm_tag)

