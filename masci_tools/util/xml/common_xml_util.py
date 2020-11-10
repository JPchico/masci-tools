# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the Masci-tools package.                               #
# (Material science tools)                                                    #
#                                                                             #
# The code is hosted on GitHub at https://github.com/judftteam/masci-tools    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
#                                                                             #
###############################################################################
"""
Common functions for parsing input/output files or XMLschemas from FLEUR
"""
from lxml import etree
from masci_tools.io.parsers.fleur.fleur_schema.schema_dict_utils import get_tag_xpath

def read_constants(xmltree,schema_dict):
   """
   Reads in the constants defined in the inp.xml
   and returns them combined with the predefined constants from
   fleur as a dictionary

   :param xmltree: xmltree of the inp.xml file
   :param schema_dict: schema_dictionary of the version of the inp.xml

   :return: a python dictionary with all defined constants
   """
   import numpy as np

   #Predefined constants in the Fleur Code
   const_dict = {'Pi': np.pi,
                 'Deg': 2*np.pi/360.0,
                 'Ang': 1.8897261247728981,
                 'nm': 18.897261247728981,
                 'pm': 0.018897261247728981,
                 'Bohr': 1.0}
   xpath_constants = get_tag_xpath(schema_dict,'constant')
   constant_elems = xmltree.xpath(xpath_constants)
   for const in constant_elems:
      name = const.attrib['name']
      value = const.attrib['value']
      if name not in const_dict:
         const_dict[name] = value
      else:
         raise KeyError('Ambiguous definition of key {name}')

   return const_dict

def clear_xml(tree, schema_dict=None):
    """
    Removes comments and executes xinclude tags of an
    xml tree. 

    :param tree: an xml-tree which will be processes
    :return: cleared_tree, an xml-tree without comments and with replaced xinclude tags

    TODO: Currently what can be included is fleur specific. 
    But this can probably easily generalized
    """
    import copy

    possible_include = ['relaxation', 'atomGroups', 'atomSpecies', 'kPointLists', 'symmetryOperations']

    cleared_tree = copy.deepcopy(tree)

    # replace XInclude parts to validate against schema
    cleared_tree.xinclude()

    if schema_dict is not None:
        # get rid of xml:base attribute in the included parts
        for include_tag in possible_include:
            try:
                include_path = get_tag_xpath(schema_dict, include_tag)
            except (ValueError,KeyError):
                continue
            included_elem = tree.xpath(include_path)
            if included_elem != []:
                included_elem = included_elem[0]
                for attribute in included_elem.keys():
                    if 'base' in attribute:
                        cleared_tree = delete_att(cleared_tree, include_path, attribute)

    # remove comments from inp.xml
    comments = cleared_tree.xpath('//comment()')
    for comment in comments:
        com_parent = comment.getparent()
        com_parent.remove(comment)

    return cleared_tree


def convert_xml_attribute(stringattribute, possible_types, constants):
    """
    Tries to converts a given string attribute to the types given in possible_types.
    First succeeded conversion will be returned

    :param stringattribute (str): Attribute to convert.
    :param possible_types (str, list of str): What types it will try to convert to
    :param constants: dict, of constants defined in fleur input
    """
    from masci_tools.util.fleur_calculate_expression import calculate_expression

    if not isinstance(possible_types, list):
        possible_types = [possible_types]
    
    for value_type in possible_types:
        if value_type == 'float':
            converted_value, suc = convert_to_float(stringattribute)
        elif value_type == 'float_expression':
            converted_value = calculate_expression(stringattribute, constants)
            suc = True
        elif value_type == 'int':
            converted_value, suc = convert_to_int(stringattribute)
        elif value_type == 'switch':
            converted_value, suc = convert_from_fortran_bool(stringattribute)
        elif value_type == 'string':
            suc = True
            converted_value = str(stringattribute)
        if suc:
            return converted_value

    return None


def convert_to_float(value_string):
    """
    Tries to make a float out of a string. If it can't it logs a warning
    and returns True or False if convertion worked or not.

    :param value_string: a string
    :return: value the new float or value_string: the string given
    :return: True if convertion was successfull, False otherwise
    """
    try:
        value = float(value_string)
    except (TypeError, ValueError):
        return value_string, False
    return value, True


def convert_to_int(value_string):
    """
    Tries to make a int out of a string. If it can't it logs a warning
    and returns True or False if convertion worked or not.

    :param value_string: a string
    :return: value the new int or value_string: the string given
    :return: True or False
    """
    try:
        value = int(value_string)
    except (TypeError, ValueError):
        return value_string, False
    return value, True


def convert_from_fortran_bool(stringbool):
    """
    Converts a string in this case ('T', 'F', or 't', 'f') to True or False

    :param stringbool: a string ('t', 'f', 'F', 'T')

    :return: boolean  (either True or False)
    """
    true_items = ['True', 't', 'T']
    false_items = ['False', 'f', 'F']
    if isinstance(stringbool, str):
        if stringbool in false_items:
            return False, True
        if stringbool in true_items:
            return True, True
        else:
            return stringbool, False
    elif isinstance(stringbool, bool):
        return stringbool, True  # no conversion needed...
    else:
        return stringbool, False


def delete_att(xmltree, xpath, attrib):
    """
    Deletes an xml tag in an xmltree.

    :param xmltree: an xmltree that represents inp.xml
    :param xpath: a path to the attribute to be deleted
    :param attrib: the name of an attribute
    """
    root = xmltree.getroot()
    nodes = root.xpath(xpath)
    if nodes:
        for node in nodes:
            try:
                del node.attrib[attrib]
            except BaseException:
                pass
    return xmltree