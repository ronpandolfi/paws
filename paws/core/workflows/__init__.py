import os
import pkgutil

wf_paths = {} 
def load_wfs_from_path(path_,pkg,cat_root=''):
    wfs = []
    cats = []
    # pkgutil.iter_modules returns module_loader, module_name, ispkg forall modules in path
    mods = pkgutil.iter_modules(path_)
    mods = [mod for mod in mods if mod[1] not in ['__init__','Workflow','WfManager','wftools']]
    for modloader, modname, ispkg in mods:
        if ispkg:
            pkg_path = [os.path.join(path_[0],modname)]
            subcat_root = modname
            if cat_root:
                subcat_root = cat_root+'.'+modname
            pkg_wfs, pkg_cats = load_wfs_from_path(pkg_path,pkg+'.'+modname,subcat_root)
            pkg_wfs = [wf for wf in pkg_wfs if not wf in wfs]
            pkg_cats = [cat for cat in pkg_cats if not cat in cats]
            wfs = wfs + pkg_wfs
            cats = cats + pkg_cats
        else:
            # assume that this module produces
            # a .wfl file of the same name.
            if not cat_root in cats:
                cats.append(cat_root)
            wfs.append( (cat_root,modname) )
            wf_path = __path__[0]
            for subcat in cat_root.split('.'):
                wf_path = os.path.join(wf_path,subcat)
            wf_path = os.path.join(wf_path,modname+'.wfl')
            wf_paths[cat_root+'.'+modname] = wf_path
    return wfs, cats

cat_wf_list, cat_list = load_wfs_from_path(__path__,__name__)

