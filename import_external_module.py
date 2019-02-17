import sys
import os

def import_external(module_path, subdir_to_search_for_module):
        # add dirs to path if necessary
    (root, ext) = os.path.splitext(module_path)
    if os.path.exists(module_path) and ext == '.py':
        # user supplied translation file directly
        sys.path.insert(0, os.path.dirname(root))
    else:
        # first check translations in the subdir translations of cwd
        sys.path.insert(0, os.path.join(os.getcwd(), subdir_to_search_for_module))
        # then check subdir of script dir
        sys.path.insert(1, os.path.join(os.path.dirname(__file__), subdir_to_search_for_module))
        # (the cwd will also be checked implicityly)

    # strip .py if present, as import wants just the module name
    if ext == '.py':
        module_path = os.path.basename(root)
    return __import__(module_path, fromlist = [''])