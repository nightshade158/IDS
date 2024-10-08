# ASN.1 named integers
from libs.pyasn1 import error

__all__ = [ 'NamedValues' ]

class NamedValues:
    def __init__(self, *namedValues):
        self.nameToValIdx = {}; self.valToNameIdx = {}
        self.namedValues = ()        
        automaticVal = 1
        for namedValue in namedValues:
            if isinstance(namedValue, tuple):
                name, val = namedValue
            else:
                name = namedValue
                val = automaticVal
            if name in self.nameToValIdx:
                raise error.PyAsn1Error('Duplicate name %s' % (name,))
            self.nameToValIdx[name] = val
            if val in self.valToNameIdx:
                raise error.PyAsn1Error('Duplicate value %s=%s' % (name, val))
            self.valToNameIdx[val] = name
            self.namedValues = self.namedValues + ((name, val),)
            automaticVal = automaticVal + 1
    def __str__(self): return str(self.namedValues)
    
    def getName(self, value):
        if value in self.valToNameIdx:
            return self.valToNameIdx[value]

    def getValue(self, name):
        if name in self.nameToValIdx:
            return self.nameToValIdx[name]
    
    def __getitem__(self, i): return self.namedValues[i]
    def __len__(self): return len(self.namedValues)

    def __add__(self, namedValues):
        return self.__class__(*self.namedValues + namedValues)
    def __radd__(self, namedValues):
        return self.__class__(*namedValues + tuple(self))
        
    def clone(self, *namedValues):
        return self.__class__(*tuple(self) + namedValues)

# XXX clone/subtype?
