#usage: sphinx-apidoc [options] -o outputdir packagedir [excluded_paths]
# -f: force overwriting of rst files
# --no-toc: do not generate a toc for the api
# -H [name]: package title
# -A [name]: authorship 

sphinx-apidoc -f -d 3 -o source/packagedoc_files ../paws/ 

# TODO: elegant op documentation
#sphinx-apidoc -f -H paws -A '2017 Lenson A. Pellouchoud' -o source/opdoc_files ../paws/core/operations/
#sphinx-apidoc -f -H paws -A '2017 Lenson A. Pellouchoud' -o source/apidoc_files ../paws/api/ 



