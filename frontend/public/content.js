chrome.runtime.onMessage.addListener((request, _, sendResponse) => {
    if (request.action === 'extractAddress') {
        const address = extractAddressFromPage();
        const numRooms = extractRoomCountFromPage();
        sendResponse({ address: address, numRooms: numRooms });
    }
});

function extractRoomCountFromPage() {
    // StreetEasy bedroom extraction patterns
    const bedroomPatterns = [
        // Look for "2 bed" or "2 bedroom" patterns
        /(\d+)\s*(?:bed|bedroom|br)(?:room)?s?/i,
        // Look for "Studio" or "Studio apartment"
        /studio/i
    ];

    // Common selectors where bedroom info might be found
    const selectors = [
        '[data-testid="listing-details"]',
        '[class*="listing-details"]',
        '[class*="unit-info"]',
        '[class*="bedroom"]',
        '[class*="details"]',
        '.listing-title',
        'h1',
        'h2',
        '[class*="summary"]'
    ];

    // Try to find bedroom info in specific elements
    for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        for (const element of elements) {
            if (element && element.textContent) {
                const text = element.textContent.trim();
                
                // Check for studio
                if (/studio/i.test(text)) {
                    return 0; // Studio = 0 bedrooms
                }
                
                // Check for bedroom count
                const bedroomMatch = text.match(/(\d+)\s*(?:bed|bedroom|br)(?:room)?s?/i);
                if (bedroomMatch) {
                    const count = parseInt(bedroomMatch[1]);
                    if (count >= 1 && count <= 10) { // Reasonable range
                        return count;
                    }
                }
            }
        }
    }

    // Fallback: search all text on page for bedroom info
    const allText = document.body.innerText;
    
    // Check for studio in page text
    if (/studio\s*apartment|studio\s*unit|studio\s*rental/i.test(allText)) {
        return 0;
    }
    
    // Look for bedroom patterns in all text
    const matches = allText.match(/(\d+)\s*(?:bed|bedroom|br)(?:room)?s?/gi);
    if (matches && matches.length > 0) {
        // Take the first reasonable bedroom count found
        for (const match of matches) {
            const numberMatch = match.match(/(\d+)/);
            if (numberMatch) {
                const count = parseInt(numberMatch[1]);
                if (count >= 1 && count <= 10) {
                    return count;
                }
            }
        }
    }

    // Default fallback if no bedroom info found
    return 1;
}

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