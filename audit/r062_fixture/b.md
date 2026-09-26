# Test Fixture B Markdown Document

This is a synthetic markdown document created specifically for the R06.2 byte-level provenance verification fixture.
It contains headings, lists, tables, and enough arbitrary prose to exceed 2048 bytes deterministically.

## Section 1: Overview
The purpose of this file is to prove that multiline markdown with code fences, indentation, and special characters
can be encoded into Base64, embedded into a container document, extracted, and decoded back into byte-for-byte
identical raw bytes with zero divergence in length or SHA-256 hash.

### Subsection 1.1: Data Table
| Index | Key | Value | Status | Hash Algorithm |
|---|---|---|---|---|
| 01 | alpha | 1048576 | VERIFIED | SHA-256 |
| 02 | beta | 2097152 | VERIFIED | SHA-256 |
| 03 | gamma | 4194304 | VERIFIED | SHA-256 |
| 04 | delta | 8388608 | VERIFIED | SHA-256 |
| 05 | epsilon | 16777216 | VERIFIED | SHA-256 |

## Section 2: Code Block Example
```python
def verify_fixture(raw_bytes: bytes, base64_payload: str) -> bool:
    import base64
    import hashlib
    decoded = base64.b64decode(base64_payload.encode('ascii'), validate=True)
    assert len(decoded) == len(raw_bytes)
    assert hashlib.sha256(decoded).hexdigest() == hashlib.sha256(raw_bytes).hexdigest()
    return True
```

## Section 3: Extended Prose and Invariants
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio. Praesent libero. Sed cursus ante dapibus diam.
Sed nisi. Nulla quis sem at nibh elementum imperdiet. Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta.
Mauris massa. Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos.
Curabitur sodales ligula in libero. Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh. Aenean quam. In scelerisque sem at dolor.
Maecenas mattis. Sed convallis tristique sem. Proin ut ligula vel nunc egestas porttitor. Morbi lectus risus, iaculis vel, suscipit quis, luctus non, massa.
Fusce ac turpis quis ligula lacinia aliquet. Mauris ipsum. Nulla metus metus, ullamcorper vel, tincidunt sed, euismod in, nibh.
Quisque volutpat condimentum velit. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos.
Nam nec ante. Sed lacinia, urna non tincidunt mattis, tortor neque adipiscing diam, a cursus ipsum ante quis turpis. Nulla facilisi.
Ut fringilla. Suspendisse potenti. Nunc feugiat mi a tellus consequat imperdiet. Vestibulum sapien. Proin quam. Etiam ultrices.
Suspendisse in justo eu magna luctus suscipit. Sed lectus. Integer euismod lacus luctus magna.
