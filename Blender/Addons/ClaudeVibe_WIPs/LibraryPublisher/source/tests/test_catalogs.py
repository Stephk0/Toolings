"""The ST3E -> ST3E_Ext rewrite. This is the load-bearing transform of the whole
publish, so it gets the closest tests: UUIDs must survive byte-for-byte, or the
published .blend files would point at catalogs that no longer exist."""

from core import catalogs

# The repo's real catalog file, verbatim.
REAL = """# This is an Asset Catalog Definition file for Blender.
#
# Empty lines and lines starting with `#` will be ignored.
# The first non-ignored line should be the version indicator.
# Other lines are of the format "UUID:catalog/path/for/assets:simple catalog name"

VERSION 1

f9ab2fa9-3a4e-491a-abaa-558cd5c029d0:ST3E:ST3E
bacd112a-8e87-47c2-afbc-818a11c75c08:ST3E/Deform:ST3E-Deform
8872522f-45b7-4541-a557-5b69bcbfcee2:ST3E/Generate:ST3E-Generate
9b90781b-f051-4cdb-9dcb-c8909914a87b:ST3E/Modify:ST3E-Modify
25b9ecc2-4cf7-41b3-83c3-152a2eccbc77:ST3E/Scatter & Instancing:ST3E-Scatter & Instancing
3c7d5e91-2b64-4f8a-9d13-6a0e5f2c8b47:ST3E/Shading:ST3E-Shading
"""

RULES = [{"from": "ST3E", "to": "ST3E_Ext"}]


def test_parse_reads_every_entry_and_the_version():
    parsed = catalogs.parse(REAL)
    assert parsed.version == "VERSION 1"
    assert len(parsed.entries) == 6
    assert parsed.entries[0].uuid == "f9ab2fa9-3a4e-491a-abaa-558cd5c029d0"
    assert parsed.entries[0].path == "ST3E"


def test_parse_keeps_spaces_and_ampersands_in_paths():
    entry = catalogs.parse(REAL).entries[4]
    assert entry.path == "ST3E/Scatter & Instancing"
    assert entry.simple_name == "ST3E-Scatter & Instancing"


def test_rewrite_preserves_every_uuid():
    result = catalogs.rewrite(REAL, RULES)
    before = {e.uuid for e in catalogs.parse(REAL).entries}
    after = {e.uuid for e in catalogs.parse(result.text).entries}
    assert before == after, "UUIDs must survive - the .blend files key on them"


def test_rewrite_renames_root_and_children():
    paths = [e.path for e in catalogs.parse(catalogs.rewrite(REAL, RULES).text).entries]
    assert paths == [
        "ST3E_Ext",
        "ST3E_Ext/Deform",
        "ST3E_Ext/Generate",
        "ST3E_Ext/Modify",
        "ST3E_Ext/Scatter & Instancing",
        "ST3E_Ext/Shading",
    ]


def test_rewrite_regenerates_simple_names():
    entries = catalogs.parse(catalogs.rewrite(REAL, RULES).text).entries
    by_path = {e.path: e.simple_name for e in entries}
    assert by_path["ST3E_Ext"] == "ST3E_Ext"
    assert by_path["ST3E_Ext/Deform"] == "ST3E_Ext-Deform"
    assert by_path["ST3E_Ext/Scatter & Instancing"] == "ST3E_Ext-Scatter & Instancing"


def test_rewrite_reports_what_it_touched():
    result = catalogs.rewrite(REAL, RULES)
    assert len(result.renamed) == 6
    assert result.unchanged == []
    assert result.uuid_map["bacd112a-8e87-47c2-afbc-818a11c75c08"] == (
        "ST3E/Deform", "ST3E_Ext/Deform"
    )


def test_rewrite_output_is_reparseable_and_keeps_the_version_line():
    reparsed = catalogs.parse(catalogs.rewrite(REAL, RULES).text)
    assert reparsed.version == "VERSION 1"
    assert len(reparsed.entries) == 6


def test_unmatched_catalogs_are_reported_not_silently_shipped():
    text = REAL + "aaaaaaaa-0000-0000-0000-000000000001:ThirdParty/Kit:ThirdParty-Kit\n"
    result = catalogs.rewrite(text, RULES)
    assert result.unchanged == ["ThirdParty/Kit"]
    assert len(result.renamed) == 6


def test_rename_matches_only_a_leading_component():
    # A catalog that merely *contains* the name must not be rewritten.
    assert catalogs.apply_renames("Vendor/ST3E", RULES) == "Vendor/ST3E"
    assert catalogs.apply_renames("ST3End/Deform", RULES) == "ST3End/Deform"
    assert catalogs.apply_renames("ST3E/Deform", RULES) == "ST3E_Ext/Deform"


def test_rules_do_not_cascade():
    # First match wins, so A->B plus B->C never turns an A into a C.
    rules = [{"from": "A", "to": "B"}, {"from": "B", "to": "C"}]
    assert catalogs.apply_renames("A/x", rules) == "B/x"


def test_empty_rules_leave_everything_alone():
    result = catalogs.rewrite(REAL, [])
    assert result.renamed == []
    assert len(result.unchanged) == 6


def test_custom_separator():
    result = catalogs.rewrite(REAL, RULES, separator="/")
    names = {e.simple_name for e in catalogs.parse(result.text).entries}
    assert "ST3E_Ext/Deform" in names


def test_stamp_is_written_as_a_comment_only():
    result = catalogs.rewrite(REAL, RULES, stamp="source commit abc1234")
    assert "# source commit abc1234" in result.text
    # Comments must never be mistaken for entries.
    assert len(catalogs.parse(result.text).entries) == 6


def test_known_uuids():
    assert len(catalogs.known_uuids(REAL)) == 6


def test_malformed_lines_are_skipped():
    text = REAL + "not-a-catalog-line\n"
    assert len(catalogs.parse(text).entries) == 6
