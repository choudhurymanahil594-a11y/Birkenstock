// Function to extract sizes from a given selector
const extractSizes = (selector) => {
    const sizeGroup = document.querySelector(selector);
    if (!sizeGroup) {
        return null; // Return null if the size group doesn't exist
    }

    const sizeItems = sizeGroup.querySelectorAll('.swatchanchor');
    return Array.from(sizeItems).map(item => {
        // Extract US size text and remove the " US" suffix
        return item.querySelector('.size-top').textContent.trim().replace(' US', '');
    });
};

// Check and extract women's sizes
const womenUSSizes = extractSizes('.wsizegroup');
if (womenUSSizes) {
    console.log('Women US Sizes:', womenUSSizes);
} else {
    console.log('No women\'s sizes found on this page.');
}

// Check and extract men's sizes
const menUSSizes = extractSizes('.msizegroup');
if (menUSSizes) {
    console.log('Men US Sizes:', menUSSizes);
} else {
    console.log('No men\'s sizes found on this page.');
}