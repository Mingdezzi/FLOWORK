from . import generic, eider

LOGIC_MAP = {
    'GENERIC': generic,
    'EIDER': eider,
}

def get_brand_logic(logic_name):
    return LOGIC_MAP.get(logic_name, generic)