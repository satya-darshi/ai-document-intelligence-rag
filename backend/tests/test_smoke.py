from app.services.cache import make_key
from app.services.ingestion import extract_pages


def test_cache_key_is_stable():
    assert make_key("hello", ["b", "a"]) == make_key("hello", ["a", "b"])


def test_plain_text_extraction(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello world")
    pages = extract_pages(path, "text/plain")
    assert len(pages) == 1
    assert pages[0].page_content == "hello world"
    assert pages[0].metadata["page"] == 1
