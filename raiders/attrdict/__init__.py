"""
attrdict contains several mapping objects that allow access to their
keys as attributes.
"""
from raiders.attrdict.mapping import AttrMap
from raiders.attrdict.dictionary import AttrDict
from raiders.attrdict.default import AttrDefault


__all__ = ['AttrMap', 'AttrDict', 'AttrDefault']
