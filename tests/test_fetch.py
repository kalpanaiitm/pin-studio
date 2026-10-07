def test_blog_post_is_parsed(page):
    assert page.kind == "blog" and page.title.startswith("How to Sell on Vinted UK")
    headings = [s.heading for s in page.sections]
    assert "Common beginner mistakes" in headings and "Home" not in page.full_text   # nav removed


def test_product_page_is_parsed(product):
    assert product.kind == "product" and product.price == "£9.99" and product.image_url
