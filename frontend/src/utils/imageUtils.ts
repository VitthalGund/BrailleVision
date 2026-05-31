/**
 * Helper to compress a data URL image to a Blob.
 */
export async function dataURLToBlob(dataUrl: string): Promise<Blob> {
  const res = await fetch(dataUrl);
  return res.blob();
}

/**
 * Resize and compress an image file/blob to a maximum width/height.
 * Helps reduce API upload latency on mobile connections.
 */
export function resizeImage(file: Blob, maxWidth = 800, maxHeight = 800): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.src = URL.createObjectURL(file);
    
    img.onload = () => {
      URL.revokeObjectURL(img.src);
      let width = img.width;
      let height = img.height;
      
      // Calculate scaled dimensions
      if (width > height) {
        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }
      } else {
        if (height > maxHeight) {
          width = Math.round((width * maxHeight) / height);
          height = maxHeight;
        }
      }
      
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Failed to get 2d context for resizing'));
        return;
      }
      
      ctx.drawImage(img, 0, 0, width, height);
      
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('Failed to compress resized canvas to blob'));
          }
        },
        'image/jpeg',
        0.80 // 80% JPEG quality compression
      );
    };
    
    img.onerror = (err) => {
      reject(err);
    };
  });
}
