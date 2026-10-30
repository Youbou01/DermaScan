"""Unit tests for EU CosIng dictionary parsing logic."""

from scripts.import_cosing import parse_annex_ii, parse_annex_iii


def test_parse_annex_ii_extracts_prohibited_substances() -> None:
    sample_annex_ii = (
        "Reference Number,Chemical name / INN,CAS Number,EC Number,Regulation,Regulated By,"
        "Other Directives/Regulations,SCCS opinions,Chemical/IUPAC Name,"
        "Identified INGREDIENTS or substances e.g.,CMR,Update date\n"
        '1,"N -(5-Chlorobenzoxazol-2-yl)acetamide","35783-57-4","-","(EC) No 1223/2009",'
        '"76/768/EEC","","","","","",17/10/2010\n'
        '2,"(2 -Acetoxyethyl)trimethylammonium hydroxide","51-84-3","200-128-9",'
        '"(EC) No 1223/2009","82/368/EEC","","","",'
        '"(*)Acetylcholine;(*)Acetylcholine bromide","",17/10/2010\n'
    )
    prohibited = parse_annex_ii(sample_annex_ii)
    assert "ACETYLCHOLINE" in prohibited
    assert "ACETYLCHOLINE BROMIDE" in prohibited
    assert "N -(5-CHLOROBENZOXAZOL-2-YL)ACETAMIDE" in prohibited


def test_parse_annex_iii_extracts_restricted_substances() -> None:
    sample_annex_iii = (
        "Reference number,Chemical name / INN,Name of Common Ingredients Glossary,"
        'CAS Number,EC Number,"Product Type, body parts",Maximum concentration in ready for use,'
        "Other,Wording of conditions of use and warnings,Regulation,Regulated By,"
        "Other Directives/Regulations,SCCS opinions,Chemical/IUPAC Name,"
        "Identified INGREDIENTS or substances e.g.,CMR,Update date\n"
        '1a,"Boric acid","BORIC ACID","10043-35-3","233-139-2","Talc","5%","","",'
        '"(EC) No 1223/2009","2005/80/EC","","","",'
        '"BORIC ACID;MEA-BORATE;ZINC BORATE","",13/06/2014\n'
    )
    restricted = parse_annex_iii(sample_annex_iii)
    assert "BORIC ACID" in restricted
    assert "MEA-BORATE" in restricted
    assert "ZINC BORATE" in restricted
