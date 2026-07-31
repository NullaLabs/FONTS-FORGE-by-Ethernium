/**
 * Ethernium DRM — Web Font Decryption Mapper
 * ──────────────────────────────────────────
 * Automatically translates standard strings into their scrambled PUA equivalents
 * on the fly, rendering text correctly using the obfuscated Ethernium font,
 * while preventing scraping and direct copy-paste font theft.
 */
const ETHERNIUM_DRM_MAP = {
    " ": "",
    "!": "",
    "\"": "",
    "#": "",
    "$": "",
    "%": "",
    "&": "",
    "'": "",
    "(": "",
    ")": "",
    "*": "",
    "+": "",
    ",": "",
    "-": "",
    ".": "",
    "/": "",
    "0": "",
    "1": "",
    "2": "",
    "3": "",
    "4": "",
    "5": "",
    "6": "",
    "7": "",
    "8": "",
    "9": "",
    ":": "",
    ";": "",
    "<": "",
    "=": "",
    ">": "",
    "?": "",
    "@": "",
    "A": "",
    "B": "",
    "C": "",
    "D": "",
    "E": "",
    "F": "",
    "G": "",
    "H": "",
    "I": "",
    "J": "",
    "K": "",
    "L": "",
    "M": "",
    "N": "",
    "O": "",
    "P": "",
    "Q": "",
    "R": "",
    "S": "",
    "T": "",
    "U": "",
    "V": "",
    "W": "",
    "X": "",
    "Y": "",
    "Z": "",
    "[": "",
    "\\": "",
    "]": "",
    "^": "",
    "_": "",
    "`": "",
    "a": "",
    "b": "",
    "c": "",
    "d": "",
    "e": "",
    "f": "",
    "g": "",
    "h": "",
    "i": "",
    "j": "",
    "k": "",
    "l": "",
    "m": "",
    "n": "",
    "o": "",
    "p": "",
    "q": "",
    "r": "",
    "s": "",
    "t": "",
    "u": "",
    "v": "",
    "w": "",
    "x": "",
    "y": "",
    "z": "",
    "{": "",
    "|": "",
    "}": "",
    "~": ""
};

/**
 * Encrypts standard text into scrambled PUA codepoints.
 * @param {string} text - The clean input text.
 * @returns {string} - The scrambled text mapped to the DRM font.
 */
function encryptEtherniumText(text) {
    return text.split('').map(char => {
        return ETHERNIUM_DRM_MAP[char] || char;
    }).join('');
}

/**
 * Scrambles all HTML elements marked with class "ethernium-drm-text".
 */
function applyEtherniumDRM() {
    const elements = document.querySelectorAll('.ethernium-drm-text');
    elements.forEach(el => {
        if (!el.dataset.drmActive) {
            el.dataset.originalText = el.textContent;
            el.textContent = encryptEtherniumText(el.textContent);
            el.dataset.drmActive = 'true';
        }
    });
}

// Apply DRM on page load
window.addEventListener('DOMContentLoaded', applyEtherniumDRM);
