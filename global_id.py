class GlobalId(object):
    elementIdCounter = 0
    elementIdCounterIncr = -1

def get_new_id():
    GlobalId.elementIdCounter += GlobalId.elementIdCounterIncr
    return GlobalId.elementIdCounter 

def set_positive():
    if GlobalId.elementIdCounter != 0:
        raise RuntimeError("You can change to positive only before any call to 'get_new_id()' was occured")
    GlobalId.elementIdCounterIncr = 1