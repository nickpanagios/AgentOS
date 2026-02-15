#!/usr/bin/env python3
"""
Screenshot tool for all agents.
Usage: python3 screenshot.py <url> [output_path]
"""
import subprocess, sys, os, tempfile

CHROMIUM = "/opt/chromium/chrome"
NODE_MODULES = "/tmp/node_modules"

def take_screenshot(url, output_path=None, width=1280, height=900, full_page=True):
    if not output_path:
        output_path = tempfile.mktemp(suffix=".png", prefix="screenshot_")
    
    js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
    const browser = await chromium.launch({{
        executablePath: '{CHROMIUM}',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }});
    const page = await browser.newPage({{ viewport: {{ width: {width}, height: {height} }} }});
    await page.goto('{url}', {{ waitUntil: 'networkidle', timeout: 30000 }}).catch(() => {{}});
    await page.waitForTimeout(1500);
    await page.screenshot({{ path: '{output_path}', fullPage: {'true' if full_page else 'false'} }});
    await browser.close();
}})();
"""
    script = tempfile.mktemp(suffix=".js")
    with open(script, "w") as f:
        f.write(js)
    try:
        r = subprocess.run(["node", script], capture_output=True, text=True, timeout=45,
                          env={**os.environ, "NODE_PATH": NODE_MODULES})
        if r.returncode != 0:
            raise RuntimeError(r.stderr[:500])
        return output_path
    finally:
        os.unlink(script)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: screenshot.py <url> [output_path]"); sys.exit(1)
    path = take_screenshot(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"Screenshot saved: {path}")
