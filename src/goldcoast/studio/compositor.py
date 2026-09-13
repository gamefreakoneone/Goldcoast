import base64
import html
import os

SIZES = {
    "landscape": (1920, 1080),
    "portrait": (1080, 1920),
    "post": (1080, 1440),
    "story": (1080, 1920),
}


def data_url(raw, mime="image/png"):
    return "data:" + mime + ";base64," + base64.b64encode(raw).decode()


def compose_html(profile, kit, brief, background, format, logo=None, font=None):
    width, height = SIZES[format]
    portrait = format == "portrait"
    family = {"sans": "Arial, sans-serif", "serif": "Georgia, serif", "mono": "monospace"}[
        kit.typography
    ]
    font_rule = ""
    if font:
        font_rule = "@font-face{font-family:Brand;src:url('" + data_url(font, "font/ttf") + "')}"
        family = "Brand," + family
    esc = html.escape
    logo_html = '<img class="logo" src="' + data_url(logo) + '" alt="">' if logo else ""
    offer_html = '<p class="offer">' + esc(brief.offer_text) + "</p>" if brief.offer_text else ""
    grid = "grid-template-rows:53% 47%" if portrait else "grid-template-columns:55% 45%"
    heading = 102 if portrait else 88
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
{font_rule}
*{{box-sizing:border-box}}html,body{{margin:0;width:{width}px;height:{height}px;overflow:hidden}}
.ad{{width:100%;height:100%;display:grid;{grid};background:{kit.palette[0]};color:{kit.palette[1]}}}
.visual{{position:relative;min-height:0;min-width:0;overflow:hidden}}
.hero{{width:100%;height:100%;object-fit:cover;display:block}}
.logo{{position:absolute;left:48px;top:48px;max-width:220px;max-height:120px;object-fit:contain;
background:white;padding:18px;border-radius:4px}}
.copy{{padding:{"62px 70px" if portrait else "70px"};display:flex;flex-direction:column;
min-width:0;min-height:0;gap:24px;font-family:Arial,sans-serif}}
.business{{margin:0;font-size:26px;font-weight:700;letter-spacing:2px}}
h1{{font-family:{family};font-size:{heading}px;line-height:1.02;letter-spacing:-3px;
margin:0;font-weight:700;overflow-wrap:break-word}}
.subtitle{{font-size:32px;line-height:1.3;margin:0;overflow-wrap:break-word}}
.offer{{font-size:30px;font-weight:700;margin:0;padding-top:6px}}
.footer{{margin-top:auto;display:flex;align-items:center;justify-content:space-between;gap:24px}}
.cta{{border:2px solid currentColor;padding:18px 26px;font-size:26px;font-weight:700}}
.location{{font-size:24px;max-width:48%;line-height:1.3}}
</style></head><body><main class="ad"><div class="visual">
<img class="hero" src="{data_url(background)}" alt="">{logo_html}</div><section class="copy">
<p class="business">{esc(profile.name)}</p><h1>{esc(brief.headline)}</h1>
<p class="subtitle">{esc(brief.subheading)}</p>{offer_html}<div class="footer">
<span class="cta">{esc(brief.cta)}</span>
<span class="location">{esc(profile.neighborhood or profile.city)}</span>
</div></section></main></body></html>'''


async def render_composite(profile, kit, brief, background, format, logo=None, font=None):
    from playwright.async_api import async_playwright

    width, height = SIZES[format]
    document = compose_html(profile, kit, brief, background, format, logo, font)
    executable = os.getenv("GOLDCOAST_CHROMIUM_EXECUTABLE")
    options = {"headless": True}
    if executable:
        options["executable_path"] = executable
    elif os.name == "nt":
        options["channel"] = "chrome"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**options)
        try:
            page = await browser.new_page(
                viewport={"width": width, "height": height}, device_scale_factor=1
            )
            await page.route("**/*", lambda route: route.abort())
            await page.set_content(document, wait_until="load")
            await page.evaluate("document.fonts.ready")
            await page.evaluate("Promise.all(Array.from(document.images).map(i => i.decode()))")
            for _ in range(8):
                overflow = await page.evaluate("""() => {
                    const copy = document.querySelector('.copy');
                    return copy.scrollHeight > copy.clientHeight + 1 ||
                        [...copy.querySelectorAll('*')].some(
                            e => e.scrollWidth > e.clientWidth + 1);
                }""")
                if not overflow:
                    break
                await page.evaluate("""() => {
                    for (const selector of ['h1', '.subtitle', '.business', '.cta', '.location']) {
                        const e = document.querySelector(selector);
                        e.style.fontSize = parseFloat(getComputedStyle(e).fontSize) * .94 + 'px';
                    }
                }""")
            else:
                raise ValueError("Creative text overflows the controlled layout")
            return await page.screenshot(type="png", animations="disabled")
        finally:
            await browser.close()
