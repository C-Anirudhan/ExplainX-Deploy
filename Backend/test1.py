import cv2
import numpy as np

# 1. Load image in Grayscale
# Make sure 'rock_inscription.jpg' is in the same folder as this script
img = cv2.imread('img.jpeg', 0)

if img is None:
    print("Error: Could not load image. Check the file name.")
else:
    # 2. Apply Black-Hat Transform (The Magic Step)
    # This extracts dark elements (letters) from bright surroundings
    # Adjust (15, 15) if your letters are thinner or thicker
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    blackhat = cv2.morphologyEx(img, cv2.MORPH_BLACKHAT, kernel)

    # 3. Enhance Contrast of the extracted grooves
    # This makes the faint grooves much brighter
    result = cv2.add(blackhat, blackhat) 

    # 4. Threshold to get your "Bicolor" image
    # Anything darker than the threshold becomes black, everything else white
    # We use INVERSE thresholding here so letters are Black on White background (paper style)
    _, binary = cv2.threshold(result, 30, 255, cv2.THRESH_BINARY_INV)

    # --- DISPLAY CODE ---
    
    # Resize images if they are too big for your screen (optional)
    def resize_for_screen(image, width=600):
        h, w = image.shape[:2]
        scale = width / w
        return cv2.resize(image, (width, int(h * scale)))

    # Show the Original
    cv2.imshow('1. Original Rock', img)

    # Show the Black-Hat (The isolated grooves/shadows)
    cv2.imshow('2. Black-Hat (Grooves)', blackhat)

    # Show the Final Result (Clean Text)
    cv2.imshow('3. Final Binary Text', binary)

    print("Press any key to close the windows...")
    
    # 5. Wait for a key press and then close
    cv2.waitKey(0)
    cv2.destroyAllWindows()