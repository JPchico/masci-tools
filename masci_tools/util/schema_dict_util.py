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
This module contains helper functions for extracting information easily from the
schema_dicts defined for the Fleur input/output

Also provides convienient functions to use just a attribute name for extracting the
attribute from the right place in the given etree
"""

from masci_tools.util.xml.common_xml_util import eval_xpath, convert_xml_text, convert_xml_attribute


def get_tag_xpath(schema_dict, name, contains=None, not_contains=None):
    """
    Tries to find a unique path from the schema_dict based on the given name of the tag
    and additional further specifications

    :param schema_dict: dict, containing all the path information and more
    :param name: str, name of the tag
    :param contains: str, this string has to be in the final path
    :param not_contains: str, this string has to NOT be in the final path

    :returns: str, xpath to the given tag

    :raises ValueError: If no unique path could be found
    """

    possible_lists = ['tag_paths']

    if 'iteration_tag_paths' in schema_dict:
        possible_lists += ['iteration_tag_paths']

    all_paths = []
    for list_name in possible_lists:
        if name in schema_dict[list_name]:
            paths = schema_dict[list_name][name]

            if not isinstance(paths, list):
                paths = [paths]
            paths = paths.copy()

            invalid_paths = []
            if contains is not None:
                for xpath in paths:
                    if contains not in xpath:
                        invalid_paths.append(xpath)

            if not_contains is not None:
                for xpath in paths:
                    if not_contains in xpath and xpath not in invalid_paths:
                        invalid_paths.append(xpath)

            for invalid in invalid_paths:
                paths.remove(invalid)

            if len(paths) == 1:
                return paths[0]

            all_paths += paths

    if len(all_paths) == 0:
        raise ValueError(f'The tag {name} has no possible paths with the current specification.\n'
                         f'contains: {contains}, not_contains: {not_contains}')
    else:
        raise ValueError(f'The tag {name} has multiple possible paths with the current specification.\n'
                         f'contains: {contains}, not_contains: {not_contains} \n'
                         f'These are possible: {all_paths}')


def get_attrib_xpath(schema_dict, name, contains=None, not_contains=None, exclude=None):
    """
    Tries to find a unique path from the schema_dict based on the given name of the attribute
    and additional further specifications

    :param schema_dict: dict, containing all the path information and more
    :param name: str, name of the attribute
    :param contains: str, this string has to be in the final path
    :param not_contains: str, this string has to NOT be in the final path
    :param exclude: list of str, here specific types of attributes can be excluded
                    valid values are: settable, settable_contains, other

    :returns: str, xpath to the tag with the given attribute

    :raises ValueError: If no unique path could be found
    """

    possible_lists = ['unique_attribs', 'unique_path_attribs', 'other_attribs']
    output = False
    if 'iteration_unique_attribs' in schema_dict:
        #outputschema
        output = True
        possible_lists += ['iteration_unique_attribs', 'iteration_unique_path_attribs', 'iteration_other_attribs']

    if exclude is not None:
        for list_name in exclude:
            possible_lists.remove(f'{list_name}_attribs')
            if output:
                possible_lists.remove(f'iteration_{list_name}_attribs')
    all_paths = []
    for list_name in possible_lists:
        if name in schema_dict[list_name]:
            paths = schema_dict[list_name][name]

            if not isinstance(paths, list):
                paths = [paths]
            paths = paths.copy()

            invalid_paths = []
            if contains is not None:
                for xpath in paths:
                    if contains not in xpath:
                        invalid_paths.append(xpath)

            if not_contains is not None:
                for xpath in paths:
                    if not_contains in xpath and xpath not in invalid_paths:
                        invalid_paths.append(xpath)

            for invalid in invalid_paths:
                paths.remove(invalid)

            if len(paths) == 1:
                return paths[0]

            all_paths += paths

    if len(all_paths) == 0:
        raise ValueError(f'The attrib {name} has no possible paths with the current specification.\n'
                         f'contains: {contains}, not_contains: {not_contains}, exclude {exclude}')
    else:
        raise ValueError(f'The attrib {name} has multiple possible paths with the current specification.\n'
                         f'contains: {contains}, not_contains: {not_contains}, exclude {exclude}\n'
                         f'These are possible: {all_paths}')


def evaluate_attribute(node,
                       schema_dict,
                       name,
                       constants,
                       contains=None,
                       not_contains=None,
                       exclude=None,
                       parser_info_out=None,
                       abspath=None):
    """
    Evaluates the value of the attribute based on the given name
    and additional further specifications with the available type information

    :param schema_dict: dict, containing all the path information and more
    :param name: str, name of the attribute
    :param constants: dict, contains the defined constants
    :param contains: str, this string has to be in the final path
    :param not_contains: str, this string has to NOT be in the final path
    :param exclude: list of str, here specific types of attributes can be excluded
                    valid values are: settable, settable_contains, other
    :param parser_info_out: dict, with warnings, info, errors, ...
    :param abspath: str, to append in front of the path

    :returns: list or single value, converted in convert_xml_attribute
    """

    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}

    attrib_xpath = get_attrib_xpath(schema_dict, name, contains=contains, not_contains=not_contains, exclude=exclude)

    if abspath is not None:
        attrib_xpath = f'{abspath}{attrib_xpath}'

    stringattribute = eval_xpath(node, f'{attrib_xpath}/@{name}', parser_info_out=parser_info_out)

    if isinstance(stringattribute, list):
        if len(stringattribute) == 0:
            parser_info_out['parser_warnings'].append(f'No values found for attribute {name}')
            return None

    possible_types = schema_dict['attrib_types'][name]

    warnings = []
    converted_value, suc = convert_xml_attribute(stringattribute,
                                                 possible_types,
                                                 constants,
                                                 conversion_warnings=warnings)

    if not suc:
        parser_info_out['parser_warnings'].append(f'Failed to evaluate attribute {name}: '
                                                  'Below are the warnings from convert_xml_attribute')
        for warning in warnings:
            parser_info_out['parser_warnings'].append(warning)

    return converted_value


def evaluate_text(node,
                  schema_dict,
                  name,
                  constants,
                  contains=None,
                  not_contains=None,
                  parser_info_out=None,
                  abspath=None):
    """
    Evaluates the text of the tag based on the given name
    and additional further specifications with the available type information

    :param schema_dict: dict, containing all the path information and more
    :param name: str, name of the tag
    :param constants: dict, contains the defined constants
    :param contains: str, this string has to be in the final path
    :param not_contains: str, this string has to NOT be in the final path
    :param parser_info_out: dict, with warnings, info, errors, ...
    :param abspath: str, to append in front of the path

    :returns: list or single value, converted in convert_xml_text
    """

    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}

    tag_xpath = get_tag_xpath(schema_dict, name, contains=contains, not_contains=not_contains)

    if abspath is not None:
        tag_xpath = f'{abspath}{tag_xpath}'

    stringtext = eval_xpath(node, f'{tag_xpath}/text()', parser_info_out=parser_info_out)

    if isinstance(stringtext, list):
        for text in stringtext.copy():
            if text.strip() == '':
                stringtext.remove(text)
    else:
        if stringtext.strip() == '':
            stringtext = []

    if isinstance(stringtext, list):
        if len(stringtext) == 0:
            parser_info_out['parser_warnings'].append(f'No text found for tag {name}')
            return None

    possible_definitions = schema_dict['simple_elements'][name]

    warnings = []
    converted_value, suc = convert_xml_text(stringtext, possible_definitions, constants, conversion_warnings=warnings)

    if not suc:
        parser_info_out['parser_warnings'].append(f'Failed to evaluate text for tag {name}: '
                                                  'Below are the warnings from convert_xml_text')
        for warning in warnings:
            parser_info_out['parser_warnings'].append(warning)

    return converted_value


def evaluate_tag(node,
                 schema_dict,
                 name,
                 constants,
                 contains=None,
                 not_contains=None,
                 parser_info_out=None,
                 abspath=None,
                 no_raise=None):
    """
    Evaluates all attributes of the tag based on the given name
    and additional further specifications with the available type information

    :param schema_dict: dict, containing all the path information and more
    :param name: str, name of the tag
    :param constants: dict, contains the defined constants
    :param contains: str, this string has to be in the final path
    :param not_contains: str, this string has to NOT be in the final path
    :param parser_info_out: dict, with warnings, info, errors, ...
    :param abspath: str, to append in front of the path

    :returns: dict, with attribute values converted via convert_xml_attribute
    """
    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}

    if no_raise is None:
        no_raise = []

    tag_xpath = get_tag_xpath(schema_dict, name, contains=contains, not_contains=not_contains)

    #Which attributes are expected
    attribs = []
    if tag_xpath in schema_dict['tag_info']:
        attribs = schema_dict['tag_info'][tag_xpath]['attribs']
    elif 'iteration_tag_info' in schema_dict:
        if tag_xpath in schema_dict['iteration_tag_info']:
            attribs = schema_dict['iteration_tag_info'][tag_xpath]['attribs']

    if not attribs:
        parser_info_out['parser_warnings'].append(f'Failed to evaluate attributes from tag {name}: '
                                                  'No attributes to parse either the tag does not '
                                                  'exist or it has no attributes')

    if abspath is not None:
        tag_xpath = f'{abspath}{tag_xpath}'

    out_dict = {}

    for attrib in attribs:

        stringattribute = eval_xpath(node, f'{tag_xpath}/@{attrib}', parser_info_out=parser_info_out)

        if isinstance(stringattribute, list):
            if len(stringattribute) == 0:
                if attrib not in no_raise:
                    parser_info_out['parser_warnings'].append(f'No values found for attribute {attrib} at tag {name}')
                out_dict[attrib] = None
                continue

        possible_types = schema_dict['attrib_types'][attrib]

        warnings = []
        out_dict[attrib], suc = convert_xml_attribute(stringattribute,
                                                      possible_types,
                                                      constants,
                                                      conversion_warnings=warnings)

        if not suc:
            parser_info_out['parser_warnings'].append(f'Failed to evaluate attribute {attrib}: '
                                                      'Below are the warnings from convert_xml_attribute')
            for warning in warnings:
                parser_info_out['parser_warnings'].append(warning)

    return out_dict


def evaluate_single_value_tag(node,
                              schema_dict,
                              name,
                              constants,
                              contains=None,
                              not_contains=None,
                              parser_info_out=None,
                              abspath=None):
    """
    Evaluates the value and unit attribute of the tag based on the given name
    and additional further specifications with the available type information

    :param schema_dict: dict, containing all the path information and more
    :param name: str, name of the tag
    :param constants: dict, contains the defined constants
    :param contains: str, this string has to be in the final path
    :param not_contains: str, this string has to NOT be in the final path
    :param parser_info_out: dict, with warnings, info, errors, ...
    :param abspath: str, to append in front of the path

    :returns: value and unit, both converted in convert_xml_attribute
    """
    if parser_info_out is None:
        parser_info_out = {'parser_warnings': []}

    value_dict = evaluate_tag(node,
                              schema_dict,
                              name,
                              constants,
                              contains=contains,
                              not_contains=not_contains,
                              parser_info_out=parser_info_out,
                              abspath=abspath,
                              no_raise=['units', 'comment'])

    if 'value' not in value_dict:
        parser_info_out['parser_warnings'].append(f'Failed to evaluate singleValue from tag {name}: '
                                                  "Has no 'value' attribute")
    if 'units' not in value_dict:
        parser_info_out['parser_warnings'].append(f'Failed to evaluate singleValue from tag {name}: '
                                                  "Has no 'units' attribute")

    return value_dict


def tag_exists(node, schema_dict, name, contains=None, not_contains=None, parser_info_out=None, abspath=None):
    """
    Evaluates whether the tag exists in the xmltree based on the given name
    and additional further specifications with the available type information

    :param schema_dict: dict, containing all the path information and more
    :param name: str, name of the tag
    :param contains: str, this string has to be in the final path
    :param not_contains: str, this string has to NOT be in the final path
    :param parser_info_out: dict, with warnings, info, errors, ...
    :param abspath: str, to append in front of the path

    :returns: bool, True if any nodes with the path exist
    """
    return get_number_of_nodes(node,
                               schema_dict,
                               name,
                               contains=contains,
                               not_contains=not_contains,
                               parser_info_out=parser_info_out,
                               abspath=abspath) != 0


def get_number_of_nodes(node, schema_dict, name, contains=None, not_contains=None, parser_info_out=None, abspath=None):
    """
    Evaluates the number of occurences of the tag in the xmltree based on the given name
    and additional further specifications with the available type information

    :param schema_dict: dict, containing all the path information and more
    :param name: str, name of the tag
    :param contains: str, this string has to be in the final path
    :param not_contains: str, this string has to NOT be in the final path
    :param parser_info_out: dict, with warnings, info, errors, ...
    :param abspath: str, to append in front of the path

    :returns: bool, True if any nodes with the path exist
    """
    tag_xpath = get_tag_xpath(schema_dict, name, contains=contains, not_contains=not_contains)

    if abspath is not None:
        tag_xpath = f'{abspath}{tag_xpath}'

    return len(eval_xpath(node, tag_xpath, parser_info_out=parser_info_out, list_return=True))
