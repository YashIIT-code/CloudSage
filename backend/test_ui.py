import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to http://localhost:8080...")
        await page.goto('http://localhost:8080/')
        
        # Wait for the drop zone to be visible
        await page.wait_for_selector('#drop-zone')
        
        print("Uploading test_data.csv...")
        # Get the absolute path
        file_path = os.path.abspath('test_data.csv')
        
        # Set the file in the hidden input
        await page.set_input_files('#file-input', file_path)
        
        # Click calculate
        print("Clicking Calculate Cost...")
        await page.click('#calculate-btn')
        
        # Wait for the results to appear (they remove the hidden class)
        print("Waiting for results...")
        await page.wait_for_selector('#results:not(.hidden)')
        
        # Give it a tiny bit of time to render
        await asyncio.sleep(0.5)
        
        print("Taking screenshot...")
        screenshot_path = os.path.abspath('../../../brain/e3973dc1-74ef-4f88-9c77-3c324394af55/cost_calculator_results.png')
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
