# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
"""
Tests of the xml_getters
"""
import pytest
import os

file_path1 = 'files/fleur/aiida_fleur/inpxml'
file_path2 = 'files/fleur/Max-R5'

inpxmlfilefolder = os.path.dirname(os.path.abspath(__file__))

inpxmlfilefolder_valid = [
    os.path.abspath(os.path.join(inpxmlfilefolder, file_path1)),
    os.path.abspath(os.path.join(inpxmlfilefolder, file_path2))
]

broken_inputs = [
    'CoHybridPBE0', 'CoUnfold', 'gw1Interface', 'GaAsWannSOC', 'TiO2eelsXML', 'gw2Interface', 'Fe_film_SS_conv',
    'SiHybrid8kpt_nosym', 'Fe_bulk_SS_conv', 'Fe_film_SSFT', 'Max-R5/NiO_ldauXML', 'Max-R5/Bi2Te3XML'
]

inp_content_input = ['FePt_film_SSFT_LO/files/inp2.xml']

inpxmlfilelist = []
inpxmlfilelist_content = []
for folder in inpxmlfilefolder_valid:
    for subdir, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.xml') and 'inp' in file:
                non_valid = False
                for broken in broken_inputs:
                    if broken in subdir:
                        non_valid = True
                if not non_valid:
                    inpxmlfilelist.append(os.path.join(subdir, file))
                    for inp_dictfolder in inp_content_input:
                        if inp_dictfolder in os.path.join(subdir, file):
                            inpxmlfilelist_content.append(os.path.join(subdir, file))


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_get_cell(load_inpxml, inpxmlfilepath):
    """
    Test that get_cell works for all input files
    """
    from masci_tools.util.xml.xml_getters import get_cell
    import numpy as np

    xmltree, schema_dict = load_inpxml(inpxmlfilepath)

    cell, pbc = get_cell(xmltree, schema_dict)

    assert isinstance(cell, np.ndarray)
    assert cell.shape == (3, 3)
    assert isinstance(pbc, list)
    assert len(pbc) == 3


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_get_structure_data(load_inpxml, inpxmlfilepath):
    """
    Test that get_cell works for all input files
    """
    from masci_tools.util.xml.xml_getters import get_structure_data
    import numpy as np

    xmltree, schema_dict = load_inpxml(inpxmlfilepath)

    atoms, cell, pbc = get_structure_data(xmltree, schema_dict)

    assert isinstance(atoms, list)
    assert len(atoms) != 0
    assert isinstance(cell, np.ndarray)
    assert cell.shape == (3, 3)
    assert isinstance(pbc, list)
    assert len(pbc) == 3


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_get_parameter_data(load_inpxml, inpxmlfilepath):
    """
    Test that get_cell works for all input files
    """
    from masci_tools.util.xml.xml_getters import get_parameter_data

    xmltree, schema_dict = load_inpxml(inpxmlfilepath)

    para = get_parameter_data(xmltree, schema_dict)

    assert isinstance(para, dict)
    assert para != {}


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_get_fleur_modes(load_inpxml, inpxmlfilepath):
    """
    Test that get_cell works for all input files
    """
    from masci_tools.util.xml.xml_getters import get_fleur_modes

    xmltree, schema_dict = load_inpxml(inpxmlfilepath)

    modes = get_fleur_modes(xmltree, schema_dict)

    assert isinstance(modes, dict)
    assert modes != {}


@pytest.mark.parametrize('inpxmlfilepath', inpxmlfilelist)
def test_get_kpoints_data(load_inpxml, inpxmlfilepath):
    """
    Test that get_cell works for all input files
    """
    from masci_tools.util.xml.xml_getters import get_kpoints_data
    import numpy as np

    xmltree, schema_dict = load_inpxml(inpxmlfilepath)

    kpoints, weights, cell, pbc = get_kpoints_data(xmltree, schema_dict)

    assert kpoints is not None
    assert weights is not None
    assert isinstance(cell, np.ndarray)
    assert cell.shape == (3, 3)
    assert isinstance(pbc, list)
    assert len(pbc) == 3
