chrome.runtime.onMessage.addListener((request, _, sendResponse) => {
    if (request.action === 'extractAddress') {
        const address = extractAddressFromPage();
        sendResponse({ address: address });
    }
});

function extractAddressFromPage() {
    const aboutBuildingSection = Array.from(document.querySelectorAll('*')).find(el =>
        el.textContent?.includes('About the building')
    );

    if (aboutBuildingSection) {
        const parent = aboutBuildingSection.parentElement;
        if (parent) {
            const siblings = Array.from(parent.children);
            for (const sibling of siblings) {
                if (sibling !== aboutBuildingSection) {
                    const text = sibling.textContent?.trim();
                    if (text && text.length > 10 && text.length < 150) {
                        const fullAddressPattern = /\d+.*[A-Z]{2}\s+\d{5}/i;
                        if (fullAddressPattern.test(text)) {
                            return text;
                        }
                    }
                }
            }
        }
    }

    // Fallback: Common StreetEasy selectors for address information
    const selectors = [
        'h1[data-testid="listing-title"]',
        '.listing-title h1',
        '[data-testid="address"]',
        '.address',
        'h1',
        '.listing-details h1',
        '[class*="address"]',
        '[class*="title"]'
    ];

    // Try each selector
    for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element && element.textContent?.trim()) {
            const text = element.textContent.trim();
            // Clean up the text (remove extra whitespace, newlines, etc.)
            const cleanText = text.replace(/\s+/g, ' ').trim();
            if (cleanText.length > 10 && cleanText.length < 150) { // Ensure it's a reasonable length for a full address
                // Check for full address format first
                const fullAddressPattern = /\d+.*[A-Z]{2}\s+\d{5}/i;
                if (fullAddressPattern.test(cleanText)) {
                    return cleanText.slice(0, -5);
                }
            }
        }
    }

    // Final fallback: look for any text that looks like a full address
    const allText = document.body.innerText;
    const fullAddressPattern = /\d+.*[A-Z]{2}\s+\d{5}/i;
    const fullMatch = allText.match(fullAddressPattern);

    if (fullMatch) {
        return fullMatch[0].slice(0, -5);
    }

    return null;
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const address = extractAddressFromPage();
        if (address) {
            console.log('WattsUp: Found address:', address);
        } else {
            console.log('WattsUp: No address found on this page');
        }
    }, 1000);
}); 