import os
import weakref
import importlib.util

class Cached(type):
    '''
    Class used as a metaclass to generate cached instances.
    Make sure create single instance with the same arguments.
    '''
    def __init__(self, *args, **kwargs):
        super(Cached, self).__init__(*args, **kwargs)
        self.__cache = weakref.WeakValueDictionary()

    def __call__(self, *args):
        if args in self.__cache:
            return self.__cache[args]
        else:
            obj = super(Cached, self).__call__(*args)
            self.__cache[args] = obj
            return obj


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, os.path.join(path, module_name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
