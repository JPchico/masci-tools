# -*- coding: utf-8 -*-
"""
Tests for the functions in xml_setters_names

These tests do not extensively test all possible functionality. this is done in the
tests for the underlying functions in xml_setters_xpaths and xml_setters_basic
"""
import os
from lxml import etree
import pytest

FILE_PATH = os.path.dirname(os.path.abspath(__file__))
TEST_INPXML_PATH = os.path.join(FILE_PATH, 'files/fleur/Max-R5/FePt_film_SSFT_LO/files/inp2.xml')


def test_create_tag(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import create_tag

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    node = eval_xpath(root, '/fleurInput/calculationSetup')

    tags = [child.tag for child in node.iterchildren()]
    tags.append('greensFunction')

    create_tag(xmltree, schema_dict, 'greensFunction')

    node = eval_xpath(root, '/fleurInput/calculationSetup')

    assert [child.tag for child in node.iterchildren()] == tags


def test_create_tag_specification(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import create_tag

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    with pytest.raises(ValueError, match='The tag lo has multiple possible paths with the current specification.'):
        create_tag(xmltree, schema_dict, 'lo')

    create_tag(xmltree, schema_dict, 'lo', contains='species')

    los_after = eval_xpath(root, '/fleurInput/atomSpecies/species/lo')

    assert [node.getparent().attrib['name'] for node in los_after] == ['Fe-1', 'Fe-1', 'Fe-1', 'Pt-1', 'Pt-1']
    assert [node.attrib.items() for node in los_after] == [[],
                                                           [('type', 'SCLO'), ('l', '0'), ('n', '3'), ('eDeriv', '0')],
                                                           [('type', 'SCLO'), ('l', '1'), ('n', '3'), ('eDeriv', '0')],
                                                           [],
                                                           [('type', 'SCLO'), ('l', '1'), ('n', '5'), ('eDeriv', '0')]]


def test_create_tag_create_parents(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import create_tag

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    node = eval_xpath(root, '/fleurInput/calculationSetup')

    tags = [child.tag for child in node.iterdescendants()]
    tags.extend(['greensFunction', 'realAxis'])

    with pytest.raises(ValueError, match="Could not create tag 'realAxis' because atleast one subtag is missing."):
        create_tag(xmltree, schema_dict, 'realAxis')

    create_tag(xmltree, schema_dict, 'realAxis', create_parents=True)

    node = eval_xpath(root, '/fleurInput/calculationSetup')

    assert [child.tag for child in node.iterdescendants()] == tags


def test_create_tag_complex_xpath(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import create_tag

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    create_tag(xmltree,
               schema_dict,
               'lo',
               contains='species',
               complex_xpath="/fleurInput/atomSpecies/species[@name='Fe-1']")

    los_after = eval_xpath(root, '/fleurInput/atomSpecies/species/lo')

    assert [node.getparent().attrib['name'] for node in los_after] == ['Fe-1', 'Fe-1', 'Fe-1', 'Pt-1']
    assert [node.attrib.items() for node in los_after] == [[],
                                                           [('type', 'SCLO'), ('l', '0'), ('n', '3'), ('eDeriv', '0')],
                                                           [('type', 'SCLO'), ('l', '1'), ('n', '3'), ('eDeriv', '0')],
                                                           [('type', 'SCLO'), ('l', '1'), ('n', '5'), ('eDeriv', '0')]]


def test_create_tag_occurrences(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import create_tag

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    create_tag(xmltree, schema_dict, 'lo', contains='species', occurrences=[-1])

    los_after = eval_xpath(root, '/fleurInput/atomSpecies/species/lo')

    assert [node.getparent().attrib['name'] for node in los_after] == ['Fe-1', 'Fe-1', 'Pt-1', 'Pt-1']
    assert [node.attrib.items() for node in los_after] == [[('type', 'SCLO'), ('l', '0'), ('n', '3'), ('eDeriv', '0')],
                                                           [('type', 'SCLO'), ('l', '1'), ('n', '3'), ('eDeriv', '0')],
                                                           [],
                                                           [('type', 'SCLO'), ('l', '1'), ('n', '5'), ('eDeriv', '0')]]


def test_set_attrib_value(load_inpxml):
    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_attrib_value

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_attrib_value(xmltree, schema_dict, 'kmax', 5.321)

    kmax = eval_xpath(root, '/fleurInput/calculationSetup/cutoffs/@Kmax')

    assert kmax == '5.3210000000'


def test_set_attrib_value_specification(load_inpxml):
    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_attrib_value

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    with pytest.raises(ValueError,
                       match='The attrib radius has multiple possible paths with the current specification.'):
        set_attrib_value(xmltree, schema_dict, 'radius', [40, 42])

    set_attrib_value(xmltree, schema_dict, 'radius', [40, 42], contains='species')

    radius = eval_xpath(root, '/fleurInput/atomSpecies/species/mtSphere/@radius')

    assert radius == ['40.0000000000', '42.0000000000']


def test_set_attrib_value_create(load_inpxml):
    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_attrib_value

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    with pytest.raises(
            ValueError,
            match=
            "Could not set attribute 'ne' on path '/fleurInput/calculationSetup/greensFunction/realAxis' because atleast one subtag is missing."
    ):
        set_attrib_value(xmltree, schema_dict, 'ne', 1000, contains='realAxis')

    set_attrib_value(xmltree, schema_dict, 'ne', 1000, contains='realAxis', create=True)

    ne = eval_xpath(root, '/fleurInput/calculationSetup/greensFunction/realAxis/@ne')

    assert ne == '1000'


def test_set_attrib_value_complex_xpath(load_inpxml):
    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_attrib_value

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_attrib_value(xmltree,
                     schema_dict,
                     'type',
                     'TEST',
                     contains='species',
                     complex_xpath="/fleurInput/atomSpecies/species[@name='Fe-1']/lo")

    lo_types = eval_xpath(root, '/fleurInput/atomSpecies/species/lo/@type')

    assert lo_types == ['TEST', 'TEST', 'SCLO']


def test_set_attrib_value_occurrences(load_inpxml):
    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_attrib_value

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_attrib_value(xmltree, schema_dict, 'type', 'TEST', contains='species', occurrences=-2)

    lo_types = eval_xpath(root, '/fleurInput/atomSpecies/species/lo/@type')

    assert lo_types == ['SCLO', 'TEST', 'SCLO']


def test_set_first_attrib_value(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_first_attrib_value

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_first_attrib_value(xmltree, schema_dict, 'type', 'TEST', contains='species')

    lo_types = eval_xpath(root, '/fleurInput/atomSpecies/species/lo/@type')

    assert lo_types == ['TEST', 'SCLO', 'SCLO']


def test_set_first_attrib_value_complex_xpath(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_first_attrib_value

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_first_attrib_value(xmltree,
                           schema_dict,
                           'type',
                           'TEST',
                           contains='species',
                           complex_xpath="/fleurInput/atomSpecies/species[@name='Pt-1']/lo")

    lo_types = eval_xpath(root, '/fleurInput/atomSpecies/species/lo/@type')

    assert lo_types == ['SCLO', 'SCLO', 'TEST']


def test_set_first_attrib_value_create(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_first_attrib_value

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    with pytest.raises(
            ValueError,
            match=
            "Could not set attribute 'U' on path '/fleurInput/atomSpecies/species/ldaU' because atleast one subtag is missing."
    ):
        set_first_attrib_value(xmltree, schema_dict, 'U', 42, contains={'species', 'ldaU'})

    set_first_attrib_value(xmltree, schema_dict, 'U', 42, contains={'species', 'ldaU'}, create=True)

    ldaU_node = eval_xpath(root, '/fleurInput/atomSpecies/species/ldaU')

    assert ldaU_node.attrib == {'U': '42.0000000000'}


def test_set_text(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_text

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_text(xmltree, schema_dict, 'comment', 'This is a test comment')

    res = eval_xpath(root, '/fleurInput/comment/text()')

    assert res == 'This is a test comment'


def test_set_text_specification_create(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_text

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    with pytest.raises(ValueError, match='The tag s has multiple possible paths with the current specification'):
        set_text(xmltree, schema_dict, 's', [False, False, False, True])

    with pytest.raises(
            ValueError,
            match=
            "Could not set text on path '/fleurInput/atomSpecies/species/torgueCalculation/greensfElements/s' because atleast one subtag is missing."
    ):
        set_text(xmltree, schema_dict, 's', [False, False, False, True], contains={'species', 'torgue'})

    set_text(xmltree, schema_dict, 's', [False, False, False, True], contains={'species', 'torgue'}, create=True)

    res = eval_xpath(root, '/fleurInput/atomSpecies/species/torgueCalculation/greensfElements/s/text()')

    assert res == ['F F F T', 'F F F T']


def test_set_text_specification_complex_xpath(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_text

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_text(xmltree,
             schema_dict,
             'kPoint', [10.0, 10.0, 10.0],
             complex_xpath='/fleurInput/cell/bzIntegration/kPointLists/kPointList/kPoint[1]')

    res = eval_xpath(root, '/fleurInput/cell/bzIntegration/kPointLists/kPointList/kPoint/text()')

    assert res == ['10.0000000000 10.0000000000 10.0000000000', '    0.250000     0.250000     0.000000']


def test_set_text_specification_occurrences(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_text

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_text(xmltree, schema_dict, 'kPoint', [10.0, 10.0, 10.0], occurrences=-1)

    res = eval_xpath(root, '/fleurInput/cell/bzIntegration/kPointLists/kPointList/kPoint/text()')

    assert res == ['   -0.250000     0.250000     0.000000', '10.0000000000 10.0000000000 10.0000000000']


def test_set_first_text(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_first_text

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_first_text(xmltree, schema_dict, 'kPoint', [10.0, 10.0, 10.0])

    res = eval_xpath(root, '/fleurInput/cell/bzIntegration/kPointLists/kPointList/kPoint/text()')

    assert res == ['10.0000000000 10.0000000000 10.0000000000', '    0.250000     0.250000     0.000000']


def test_set_first_text_complex_xpath(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_first_text

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    set_first_text(xmltree,
                   schema_dict,
                   'kPoint', [10.0, 10.0, 10.0],
                   complex_xpath='/fleurInput/cell/bzIntegration/kPointLists/kPointList/kPoint[2]')

    res = eval_xpath(root, '/fleurInput/cell/bzIntegration/kPointLists/kPointList/kPoint/text()')

    assert res == ['   -0.250000     0.250000     0.000000', '10.0000000000 10.0000000000 10.0000000000']


def test_set_first_text_create(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import set_first_text

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    with pytest.raises(ValueError, match='The tag s has multiple possible paths with the current specification'):
        set_first_text(xmltree, schema_dict, 's', [False, False, False, True])

    with pytest.raises(
            ValueError,
            match=
            "Could not set text on path '/fleurInput/atomSpecies/species/torgueCalculation/greensfElements/s' because atleast one subtag is missing."
    ):
        set_first_text(xmltree, schema_dict, 's', [False, False, False, True], contains={'species', 'torgue'})

    set_first_text(xmltree, schema_dict, 's', [False, False, False, True], contains={'species', 'torgue'}, create=True)

    res = eval_xpath(root, '/fleurInput/atomSpecies/species/torgueCalculation/greensfElements/s/text()')

    assert res == 'F F F T'


def test_add_number_to_attrib(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    add_number_to_attrib(xmltree, schema_dict, 'kmax', 10)

    res = eval_xpath(root, '/fleurInput/calculationSetup/cutoffs/@Kmax')

    assert res == '14.0000000000'


def test_add_number_to_attrib_rel(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    add_number_to_attrib(xmltree, schema_dict, 'kmax', 10, mode='rel')

    res = eval_xpath(root, '/fleurInput/calculationSetup/cutoffs/@Kmax')

    assert res == '40.0000000000'


def test_add_number_to_attrib_specification(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    with pytest.raises(ValueError,
                       match='The attrib radius has multiple possible paths with the current specification.'):
        add_number_to_attrib(xmltree, schema_dict, 'radius', 0.5)

    add_number_to_attrib(xmltree, schema_dict, 'radius', 0.5, not_contains='Group')

    res = eval_xpath(root, '/fleurInput/atomSpecies/species/mtSphere/@radius')

    assert res == ['2.7000000000', '2.7000000000']


def test_add_number_to_attrib_complex_xpath(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    add_number_to_attrib(xmltree,
                         schema_dict,
                         'radius',
                         0.5,
                         not_contains='Group',
                         complex_xpath="/fleurInput/atomSpecies/species[@name='Pt-1']/mtSphere")

    res = eval_xpath(root, '/fleurInput/atomSpecies/species/mtSphere/@radius')

    assert res == ['2.20000000', '2.7000000000']


def test_add_number_to_attrib_occurrences(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    add_number_to_attrib(xmltree, schema_dict, 'radius', 0.5, not_contains='Group', occurrences=[0])

    res = eval_xpath(root, '/fleurInput/atomSpecies/species/mtSphere/@radius')

    assert res == ['2.7000000000', '2.20000000']


def test_add_number_to_first_attrib(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_first_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    add_number_to_first_attrib(xmltree, schema_dict, 'kmax', 10)

    res = eval_xpath(root, '/fleurInput/calculationSetup/cutoffs/@Kmax')

    assert res == '14.0000000000'


def test_add_number_to_first_attrib_rel(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_first_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    add_number_to_first_attrib(xmltree, schema_dict, 'kmax', 10, mode='rel')

    res = eval_xpath(root, '/fleurInput/calculationSetup/cutoffs/@Kmax')

    assert res == '40.0000000000'


def test_add_number_to_first_attrib_specification(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_first_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    with pytest.raises(ValueError,
                       match='The attrib radius has multiple possible paths with the current specification.'):
        add_number_to_first_attrib(xmltree, schema_dict, 'radius', 0.5)

    add_number_to_first_attrib(xmltree, schema_dict, 'radius', 0.5, not_contains='Group')

    res = eval_xpath(root, '/fleurInput/atomSpecies/species/mtSphere/@radius')

    assert res == ['2.7000000000', '2.20000000']


def test_add_number_to_first_attrib_complex_xpath(load_inpxml):

    from masci_tools.util.xml.common_xml_util import eval_xpath
    from masci_tools.util.xml.xml_setters_names import add_number_to_first_attrib

    xmltree, schema_dict = load_inpxml(TEST_INPXML_PATH)
    root = xmltree.getroot()

    add_number_to_first_attrib(xmltree,
                               schema_dict,
                               'radius',
                               0.5,
                               not_contains='Group',
                               complex_xpath="/fleurInput/atomSpecies/species[@name='Pt-1']/mtSphere")

    res = eval_xpath(root, '/fleurInput/atomSpecies/species/mtSphere/@radius')

    assert res == ['2.20000000', '2.7000000000']
