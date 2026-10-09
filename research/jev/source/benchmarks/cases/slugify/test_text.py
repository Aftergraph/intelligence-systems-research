from text import slugify

def test_spaces_become_hyphens(): assert slugify("Hello World") == "hello-world"
def test_runs_collapse(): assert slugify("  API___Gateway  v2 ") == "api-gateway-v2"
def test_edges_trim(): assert slugify("--Hello--") == "hello"
